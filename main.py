import os
import subprocess
import re
import click
from datetime import datetime, time, timedelta




def is_time_between(begin_time, end_time, check_time=None):
    # If check time is not given, default to current UTC timexx`
    check_time = check_time or datetime.utcnow().time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else:  # crosses midnight
        return check_time >= begin_time or check_time <= end_time



@click.command()
@click.option('-f', '--folder', 'image_folder', help='ZoneMinder Camera Folder')
@click.option('-n', '--name', 'output_name', help='Output file Name')
@click.option('--fps', default=30, help='Frames per second')
@click.option('--frame_skip', default=0, help='Frame Skip Rate')
@click.option('-d', '--days_since_today', default=50, help='Days to render in timelapse before today')
@click.option('--daytime_only', default=False, help='Only include daytime in timelapse')
@click.option('--cuda', default=False, help='Render timelapse with CUDA FFMPEG extensions')
def create_timelapse(image_folder, output_name, frame_skip=0, days_since_today=50, fps=30, daytime_only=False,
                     cuda=False):
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

    text_file = open('image_list.temp', "wt")
    text_file.write(ffpeg_image_str)
    text_file.close()
    print('{} frames to render'.format(frame_count))

    if cuda:
        os.system('~/bin/ffmpeg -threads 8 -hwaccel cuvid -c:v mjpeg_cuvid -r {} -y -safe 0 ' \
                  '-f concat -i br_last3_image_files -c:v hevc_nvenc -c:a ac3 -preset slow -b:v 8M GPU_{}'
                  .format(fps, final_name))

    else:
        with click.progressbar(length=frame_count,
                               label='Rendering Timelapse') as bar:
            # os.system('ffmpeg -r {} -y -safe 0 -f concat -i image_list.temp -b:v 8M {}'.format(fps, final_name))
            process = subprocess.Popen('ffmpeg -r {} -y -safe 0 -f concat -i image_list.temp -b:v 8M {}'.format(fps, final_name),
                                       shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            last_frame_count = 0
            while process.returncode is None:
                # handle output by direct access to stdout and stderr
                for line in process.stderr:
                    if str(line).startswith('frame= '):
                        frame = re.findall('(\.?\d*)\W?(?:fps|P)', line)
                        if frame:
                            # print(line)
                            bar.update(int(frame[0])-last_frame_count)
                            last_frame_count = int(frame[0])
                # set returncode if the process has exited
                process.poll()
        # os.system('rm -f image_list.temp')


# create_timelapse('zoneminder/zm_camera_1', frame_skip=20, days_since_today=20, fps=90, output_name='street')
if __name__ == '__main__':
    create_timelapse()
    exit(0)
