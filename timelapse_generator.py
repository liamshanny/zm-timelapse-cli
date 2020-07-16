import os
import subprocess
import re
import click
from datetime import datetime, time, timedelta, tzinfo
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
@click.option('-d', '--days-since-now', 'days_since_now', default=None, type=int,
              help='Number of days to include in the timelapse before today')
@click.option('--hours-since-now', 'hours_since_now', default=None, type=int,
              help='Number of days to include in the timelapse before today')
@click.option('--daytime-only', 'daytime_only', is_flag=True, default=False,
              help='Only include images created between time(11, 00),'
                   'time(21, 30) in timelapse')
@click.option('--sunrise', default='08', help='--daytime-only sunrise', type=int)
@click.option('--sunset', default='20', help='--daytime-only sunset', type=int)
@click.option('--timezone', 'timezone_string', default='US/Eastern', help='pytz Timezone code', type=str)
@click.option('--ffmpeg-binary', 'ffmpeg_binary', default='ffmpeg', help='Alternate FFMPEG binary location',
              envvar='ZM_TIMELAPSE_FFMPEG_BINARY')
@click.option('--codec', help='FFMPEG Encoding codec', envvar='ZM_TIMELAPSE_CODEC')
@click.option('--cuda', is_flag=True, default=False, help='Render timelapse with CUDA FFMPEG extensions')
@click.option('--fps', default=30, help='Frames per second')
@click.option('--quality', default='23', help='Video Quality. 0 is best, 51 is worst', envvar='ZM_TIMELAPSE_BITRATE')
@click.help_option('-h')
def create_timelapse(image_folder, sunrise, sunset, timezone_string, output_name, quality, frame_skip=0,
                     days_since_now=None, hours_since_now=None, fps=30, daytime_only=False,
                     cuda=False, ffmpeg_binary='ffmpeg', codec=None):
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
    # date_list = [(base - timedelta(days=x)).strftime('%Y-%m-%d') for x in range(days_since_now)]
    if days_since_now:
        offset = timedelta(days=days_since_now)
    elif hours_since_now:
        offset = timedelta(hours=hours_since_now)
    else:
        offset = timedelta(days=10000000)
    # print(date_list)
    final_name = '{}_{}-days_{}fps.mp4'.format(output_name, datetime.now().strftime('%Y-%m-%d_%H:%M:%S'), fps)
    ffpeg_image_str = ''
    frame_count = 0

    print('Grabbing image files')
    for date_dir in sorted(os.listdir(image_folder)):
        if date_dir.endswith('.log'):
            continue
        for event in sorted(os.listdir(os.path.join(image_folder, date_dir))):
            event_date = datetime.utcfromtimestamp(os.path.getctime(os.path.join(image_folder, date_dir, event)))
            if (datetime.utcnow() - event_date) > offset:
                continue
            for file in sorted(os.listdir(os.path.join(image_folder, date_dir, event))):
                img_file = str(os.path.join(image_folder, date_dir, event, file))
                if img_file.endswith('.jpg') and 'snapshot' not in img_file:
                    if frame_skip_counter <= frame_skip:
                        frame_skip_counter += 1
                        continue
                    if frame_skip_counter > frame_skip:
                        date = datetime.utcfromtimestamp(os.path.getctime(img_file))
                        date_est = date - timedelta(hours=4)
                        if (datetime.utcnow() - date) < offset:
                            if daytime_only:
                                if is_time_between(time(sunrise, 00), time(sunset, 00), check_time=date_est.time()):
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
                     ' -i .image_list.temp -c:v {codec} -c:a ac3 -preset medium GPU_{final_name}' \
            .format(ffmpeg_binary=ffmpeg_binary, fps=fps, codec=codec, final_name=final_name)
    else:
        ffmpeg_str = '{ffmpeg_binary} -r {fps} -y -safe 0 -f concat -i .image_list.temp -preset fast -c:v {codec} -crf {quality} {final_name}' \
            .format(ffmpeg_binary=ffmpeg_binary, fps=fps, codec=codec, quality=quality, final_name=final_name)
    with click.progressbar(length=frame_count,
                           label='Rendering Timelapse') as bar:
        print(ffmpeg_str)
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
                else:
                    print(line)

            # set returncode if the process has exited
            process.poll()
    os.system('rm -f .image_list.temp')


if __name__ == '__main__':
    create_timelapse()
    exit(0)
