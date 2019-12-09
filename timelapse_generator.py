import os
import subprocess
import re
import click
from datetime import datetime, time, timedelta
import qprompt


def is_time_between(begin_time, end_time, check_time=None):
    # If check time is not given, default to current UTC timexx`
    check_time = check_time or datetime.utcnow().time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else:  # crosses midnight
        return check_time >= begin_time or check_time <= end_time


@click.command()
@click.option('-f', '--folder', 'image_folder', help='ZoneMinder Camera Folder', prompt=True,
              envvar='ZM_TIMELAPSE_FOLDER')
@click.option('-n', '--name', 'output_name', help='Output file Name', prompt=True)
@click.option('--frame-skip', 'frame_skip', default=0, help='Frame Skip Rate')
@click.option('-d', '--days-since-today', 'days_since_today', default=5,
              help='Number of days to include in the timelapse before today')
@click.option('--daytime-only', 'daytime_only', default=False, help='Only include images created between time(11, 00),'
                                                                    'time(21, 30) in timelapse')

@click.option('--ffmpeg-binary', 'ffmpeg_binary', default='ffmpeg', help='Alternate FFMPEG binary location',
              envvar='ZM_TIMELAPSE_FFMPEG_BINARY')
@click.option('--codec', help='FFMPEG Encoding codec', envvar='ZM_TIMELAPSE_CODEC')
@click.option('--cuda', is_flag=True, default=False, help='Render timelapse with CUDA FFMPEG extensions')
@click.option('--fps', default=30, help='Frames per second')
@click.option('--bitrate', default='8M', help='Video Bitrate', envvar='ZM_TIMELAPSE_BITRATE')

@click.help_option('-h')
def create_timelapse(image_folder, output_name, frame_skip=0, days_since_today=5, fps=30, daytime_only=False,
                     cuda=False, ffmpeg_binary='ffmpeg', codec=None, bitrate='8M'):
    """
    Example: zm-timelapse -f 'zoneminder/zm_camera_1' -n 'test' --fps 30 --frame-skip 150 --codec libx264

    Environment Variables:
    ZM_TIMELAPSE_FOLDER: --folder
    ZM_TIMELAPSE_CODEC: --codec
    ZM_TIMELAPSE_FFMPEG_BINARY: --ffmpeg-binary
    ZM_TIMELAPSE_BITRATE: --bitrate

    """
    if not codec:
        menu = qprompt.Menu()
        menu.add("1", "libx264")
        menu.add("2", "libx265")
        if cuda:
            menu.add('3', "hevc_nvenc")
            menu.add('4', 'h264_nvenc')
        codec = menu.show(returns="desc", header='Select a FFMPEG Codec')
    frame_skip_counter = 0
    base = datetime.today()
    date_list = [(base - timedelta(days=x)).strftime('%Y-%m-%d') for x in range(days_since_today)]
    # print(date_list)
    final_name = '{}_{}_{}-days_{}-fps.mp4'.format(output_name, base.strftime('%Y-%m-%d'), days_since_today, fps)
    ffpeg_image_str = ''
    frame_count = 0

    print('Grabbing image files')
    for date_dir in sorted(os.listdir(image_folder)):
        # print(date_dir)
        if date_dir not in date_list:
            continue
        for event in sorted(os.listdir(os.path.join(image_folder, date_dir))):
            # print(event)
            for file in sorted(os.listdir(os.path.join(image_folder, date_dir, event))):
                img_file = str(os.path.join(image_folder, date_dir, event, file))
                if img_file.endswith('.jpg'):
                    if frame_skip_counter <= frame_skip:
                        frame_skip_counter += 1
                        continue
                    if frame_skip_counter > frame_skip:
                        if daytime_only:
                            date = datetime.utcfromtimestamp(os.path.getctime(img_file)).time()
                            if is_time_between(time(11, 00), time(21, 30), check_time=date):
                                frame_skip_counter = 0
                                frame_count += 1
                                ffpeg_image_str += 'file \'{}\' \n'.format(img_file)
                        else:
                            # print(img_file)
                            frame_skip_counter = 0
                            frame_count += 1
                            ffpeg_image_str += 'file \'{}\' \n'.format(img_file)

    text_file = open('.image_list.temp', "wt")
    text_file.write(ffpeg_image_str)
    text_file.close()
    print('{} frames to render'.format(frame_count))

    ffmpeg_str = ''
    if cuda:
        ffmpeg_str = '{ffmpeg_binary} -threads 8 -hwaccel cuvid -c:v mjpeg_cuvid -r {fps} -y -safe 0 ' '-f concat' \
                     ' -i .image_list.temp -c:v {codec} -c:a ac3 -preset slow -b:v {bitrate} GPU_{final_name}' \
            .format(ffmpeg_binary=ffmpeg_binary, fps=fps, codec=codec, bitrate=bitrate, final_name=final_name)
    else:
        ffmpeg_str = '{ffmpeg_binary} -r {fps} -y -safe 0 -f concat -i .image_list.temp -c:v {codec} -b:v {bitrate} {final_name}' \
            .format(ffmpeg_binary=ffmpeg_binary, fps=fps, codec=codec, final_name=final_name, bitrate=bitrate)
    with click.progressbar(length=frame_count,
                           label='Rendering Timelapse') as bar:
        process = subprocess.Popen(ffmpeg_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   universal_newlines=True)
        last_frame_count = 0
        while process.returncode is None:
            # handle output by direct access to stdout and stderr
            for line in process.stderr:
                # print(line)
                if str(line).startswith('frame='):
                    frame = re.findall('(\.?\d*)\W?(?:fps|P)', line)
                    if frame:
                        # print(line)
                        curr_frame_count = int(frame[0]) - last_frame_count
                        last_frame_count = int(frame[0])
                        bar.update(curr_frame_count)


            # set returncode if the process has exited
            process.poll()
    os.system('rm -f .image_list.temp')


if __name__ == '__main__':
    create_timelapse()
    exit(0)
