from math import ceil
from os import getcwd, listdir, path
from os.path import isdir, isfile, join
from platform import system
from re import search, match
from sys import exit as sys_exit, argv
from threading import Thread
from time import sleep, time
from typing import List, Tuple, Optional, Union

import pexpect
from pexpect import popen_spawn

# File extensions supported. Any file having an extension outside of these will be ignored.
# Extensions can be added as needed. Adding incorrect extension will result in an error from ffmpeg.
audio_files = ['wav', 'mp3', 'm4a']
video_files = ['mp4', 'mkv']
# Also, these lists do not contain `flac` as a valid extension, why will anyone want
# to generate a flac file from a flac file :p

# Name of directory that to be ignored. Blank string indicates no directory is to be ignored.
ignore_dir: str = '.ignore'

# Total number of bars (hashes by default) present in the progress bar.
progress_bar_count: int = 20

# Symbol used to generate the progress bar. Max length of 4 characters.
#
# WARNING: Setting this symbol to be anything other than a blank string will replace
# the original progress bar with this symbol.
symbol: str = ''

# List containing full paths of all the files to be processed.
files = list()

# List containing strings that will be used as units of time - in reversed order.
units: List[str] = [
    'weeks',
    'days',
    'hours',
    'minutes',
    'seconds'
]

# Amount(s) of time. Global variable to avoid having to recalculate the same value(s).
time_units: List[int] = [
    60 * 60 * 24 * 7,  # Weeks
    60 * 60 * 24,  # Days
    60 * 60,  # Hours
    60,  # Minutes
    1  # Seconds
]

# Setting the name of the process depending on the host OS.
if 'windows' in system().lower():
    process_name = 'ffmpeg.exe'
else:
    process_name = 'ffmpeg'


def get_file_list(root_dir: str, mode: str = 'recursive') -> List[str]:
    """
        Returns a list of strings, each of these strings contains the full path
        of a file present inside the given location directory.


        Parameters
        -----------
        root_dir:
            A string containing the directory that is to be used as the root where
            the files are to be searched in\n
        mode:
            A string indicating the mode that is to be used to select files in the given
            directory. Default Value: 'recursive', Allowed Values: (recursive/direct)


        Remarks
        --------
        Recursive mode will select all the files that are present anywhere inside the given
        directory including the files present in a sub-directory of the root directory.

        Direct mode will simply select the files that are present in the root directory.
        Files present inside a child directory of the root directory will not be included.

        Exceptions
        ------------
        OSError.FileNotFoundError: Thrown if a directory at the location provided does not exist.


        Returns
        --------
        Each file found will be appended to the global `files` list from where it can be
        retrieved by the calling function once the execution of this function ends. And the same
        list will also be returned by this method.
    """

    if not isdir(root_dir):
        raise FileNotFoundError(f'The directory "{root_dir}" does not exist')

    items = listdir(root_dir)

    for item in items:
        # Appending all the files of the supported types to the list of files found.
        item: str = join(root_dir, item)
        ext: str = item.rpartition('.')[-1]
        if isfile(item) and (ext in audio_files or ext in video_files):
            files.append(item)

    # Recursively running this function for each directory present in the root
    # if the mode is recursive.
    if mode == 'recursive':
        for item in items:
            if item == ignore_dir:
                # If the name of any item is the same as the title of the directory
                # that is to be ignored, then skipping the item.
                # Since this loop is meant for directories only, even if the item
                # is a file no harm is done by ignoring it.
                continue

            item = join(root_dir, item)
            if isdir(item):
                get_file_list(item, mode)

    return files


def animated_exit() -> None:
    """
        Implements a nice little animation while waiting for the user to give an input
        to the script.

        Remarks
        --------
        Designed to be used to get user input only before the script quits.

        Once the user passes an input to this method, the script will be force killed by this method
    """

    # Vertical spacing to make sure that the animated effect is not lost in a sea of text.
    print('\n\n\n')

    # Boolean to ensure a parallel thread asking for user input is executed only once in the
    # infinite loop. Without this check, a new thread will be created in each iteration.
    take_input: bool = False

    thread: Optional[Thread] = None
    while True:
        message: str = 'Enter any input to exit'
        print(f'\r{message}', end='')
        sleep(1)
        print(f'\r{" " * len(message)}', end='')
        sleep(0.5)

        # Starting a parallel thread that will be blocked till the user enters any input.
        if not take_input:
            thread = Thread(target=input)
            thread.start()
            take_input = True

        # Dead thread signifies that the user has entered an input, killing the script.
        if not thread.is_alive():
            sys_exit()


def print_time(seconds: int) -> str:
    """
        Converts a number of seconds into a human-readable format and parses it into a string.

        Parameters
        -----------
        seconds: Integer containing the amount of seconds. Should be a positive whole number \n.

        Exceptions
        -----------
        TypeError: Thrown if the parameter isn't an integer \n.
        ValueError: Thrown if the argument passed is less than zero \n.

        Returns
        --------
        String containing the amount of time in readable format.
    """

    if not isinstance(seconds, int):
        raise TypeError(f'The value of `seconds` should be an integer.')
    elif seconds < 0:
        raise ValueError(f'Value of `seconds` too low [{seconds}]')

    if seconds == 0:
        # Hardcoded solution to handle cases where the time remaining is 0 seconds.
        return '0 seconds'

    global time_units, units

    # NOTE:
    # Ensure that the values in `units` and `time_units` are in same order - at the same index, both
    # the list contain values for the same time units.

    readable_time: str = ''

    temp_counter: int = 0
    while min([len(time_units), len(units)]) > temp_counter:
        if seconds >= time_units[temp_counter]:
            cal = int(seconds / time_units[temp_counter])
            readable_time += str(cal) + ' ' + units[temp_counter] + ' '
            seconds %= time_units[temp_counter]
        temp_counter += 1

    return readable_time.strip()


def animated_progress(frame_count: int, total_frames: any, time_elapsed: int) -> None:
    """
        Prints a progress bar to the screen with (hopefully) relevant data.

        Parameters
        -----------
        frame_count: Integer containing the number of frames that have been currently processed.
        Should be less than or equal to `total_frames` and greater than or equal to zero \n
        total_frames: Total number of frames. Used to calculate the current progress. Integer. \n
        If the frame count can't be fetched, this variable should be a boolean (false preferably) \n
        time_elapsed: Count of seconds elapsed before reaching this frame since the processing
        of the current file started, should be a positive integer. Used to calculate ETA. Integer \n

        Exceptions
        -----------
        TypeError: Thrown if arguments don't match type hinting. \n
        ValueError: Thrown if any of the arguments is less than zero, or if value of `frame_count`
        is greater than the value of `total_frames` \n
    """

    # Note: While checking if the value of `total_frames` is a boolean or an integer, do NOT use
    # `isinstance(total_frames, int)`, booleans can be implicitly converted into integers, the check
    # will always return true. The reverse is not true, i.e. if `total_frames` contains an integer,
    # `isinstance(total_frames, bool)` will not be true. The latter is used to check for the value
    # of `total_frames` in this section.

    if not isinstance(frame_count, int) or not isinstance(time_elapsed, int):
        raise Exception.TypeError('Non-integer argument supplied.')
    elif frame_count < 0:
        raise ValueError(f'Frame count [{frame_count}] can\'t be negative')
    elif not isinstance(total_frames, bool) and total_frames <= 0:
        # If `total_frames` is an integer and contains a value of less than or equal to 0,
        # throwing an error.
        raise ValueError(f'Total frames [{total_frames}] too less.')

    if frame_count > total_frames:
        # Ensuring that the current frame count isn't larger than the total count.
        raise ValueError(f'Current frame count [{frame_count}] cannot be greater '
                         f'than total frame count [{total_frames}]')
    elif time_elapsed < 0:
        raise ValueError(f'Time elapsed [{time_elapsed}] can\'t be negative')
    elif not isinstance(total_frames, int) and not isinstance(total_frames, bool):
        # Throwing this error only if `frame_count` is neither an integer nor a boolean.
        raise ValueError(f'Unexpected value in total frames: {total_frames}')

    percentage: Union[float, str] = 0.0
    if not isinstance(total_frames, bool):
        # The progress will be shown with a progress bar, each bar representing a fixed percentage.
        percentage: float = round(float(frame_count / total_frames) * 100, 2)

    # Calculating the number of seconds remaining to complete- the number of frames being processed
    # in a single second, divided by the total number of frames.
    eta: int = 0
    if time_elapsed > 0:
        eta = int(total_frames / float(frame_count / time_elapsed))

    # The value of `eta` right now is the amount of seconds required to process the entire file
    # from beginning. But, a certain amount of time has already elapsed. Removing that time
    # to get the time remaining.
    eta = eta - time_elapsed

    progress: str = ''
    bar_size: float = float(100 / progress_bar_count)

    # Note: At the end of this block of code, the value inside `percentage` will be a string.
    if not isinstance(total_frames, bool):
        if len(symbol) != 0:
            # If the string is not empty, generating a progress bar using the symbol.
            hashes: int = int(percentage / bar_size)
            progress = (symbol * hashes) + \
                       (' ' * (progress_bar_count - hashes))
        else:
            # If no symbol is set, using the block-y progress bar.
            completed: int = ceil(percentage / bar_size)
            progress = '█' * completed
            progress += ((progress_bar_count - completed) * ' ')

        # If the last digit after decimal in `percentage` is zero, it'll be ignored this will
        # result in variable length of string - causing problems as the previous message is to be
        # overwritten. Variable length will make the output messy. Handling that by ensuring the
        # float consists of a atleast 4 char (including the dot), and 2 digit precision.
        percentage = '%04.02f' % percentage

        # Adding percentage symbol to the string and setting the length to be '7' as the maxima
        # allowed in the string is '100.00%', following the same logic as above - padding it with
        # spaces on the left.
        percentage = (str(percentage) + '%').rjust(7)
    else:
        # Control reaches this part only when the total frame count is unknown. Replacing percentage
        # with current frame count.
        percentage = f'Frames: {frame_count}'

    # Printing what is available in the progress bar. If the total frame count is not available
    # then neither will be the current percentage, and so the progress also can't be displayed.
    print(

        # Percentage will always have a value
        f'\r\t{percentage}',

        # Printing the progress only if it is not a boolean.
        progress if not isinstance(total_frames, bool) else '',

        # Printing the remaining time if total frame count is available.
        'Remaining: {0}'.format(
            print_time(eta) if not isinstance(total_frames, bool) else "¯\\_(ツ)_/¯"),

        # Separating each part of the string with some extra space.
        sep=' ' * 4,

        # This line is to be over-written, the cursor should not jump to the next line.
        end=' '
    )


def generate_flac_file(original_file: str, *, overwrite: bool = False) -> Tuple[bool, str]:
    """
        Will generate the flac file and save it in the destination directory as required.

        Remarks
        --------
        Take in the original file that is to be converted into a flac file, use ffmpeg in the
        backend to generate a flac file with the same name as the original and save the file in the
        same directory as the original file.

        This function handles the most important task of this script, it also has the highest
        probability of an unexpected failure/crash.

        *Realizes that deleting this method will leave bug-free code*

        (╯°□°）╯︵ ┻━┻

        Exceptions
        -----------
        OSError.FileNotFoundError: Path supplied for the original file is invalid or it points to
        a directory instead of a file.

        Parameters
        -----------
        original_file: Full file path of the original file which is to be converted to flac \n
        overwrite: Boolean indicating if a file should be overwritten or not. Default --> false \n

        Returns
        --------
        A tuple containing a boolean and a string. The value of the boolean is true if the flac 
        file is generated successfully, false in case of any error.

        If any error occurs, the message will be printed directly to the screen by this method,
        the part of returning the error message to the calling function is not required.

        If the value of the boolean is true, the string will contain the full path of the flac 
        file generated. In case if the value of the boolean is false, the string will be empty.
    """

    if not isfile(original_file):
        raise FileNotFoundError(f'No file found at the path "{original_file}"')

    global process_name

    # Getting the directory in which the original file is stored, creating a new path for the flac
    # file using this location.
    directory, file_name = path.split(original_file)
    flac_file = join(directory, file_name.rpartition('.')[0]) + '.flac'

    # Firing a blank input at ffmpeg to get the number of frames in the file. This will result in a
    # warning as ffmpeg is not to be used to get file info -- `ffprobe` is an alternative
    # for this - not everyone will be willing to install ffprobe just for this, going with this
    # hack-y approach to get the number of frames in the video.
    info_command = f'{process_name} -i "{original_file}"'
    thread = popen_spawn.PopenSpawn(info_command)

    # Once the process finishes, getting the result from the command.
    output = str(thread.read())

    try:
        output = output.replace('\\r', '').replace('\\n', '')
        # Using regex to get string containing number of frames, extracting just the digits out of
        # the string - and converting into integer.
        frame_count = int(search('[0-9]+', search(r'NUMBER_OF_FRAMES-[a-zA-Z]+:(\s*)[0-9]+', output)
                                 .group()).group().strip())
    except Exception:
        # If the dialog does not contain count - flow-of-control end here. Setting `frame_count`
        # to be false. Used to know that the frame length of the file could not be detected.
        frame_count = False

    # Creating a string for all the arguments that will be used along with the ffmpeg base command.
    command = f'{process_name} -i "{original_file.strip()}" -c:a flac "{flac_file.strip()}"'

    if overwrite:
        # If existing files are to be overwritten, appending '-y' to ffmpeg command.
        command += ' -y'

    # Getting the start time before firing the process.
    start_time: int = int(time())

    # Creating a process that uses ffmpeg along the with the parameters to generate a flac file.
    thread = popen_spawn.PopenSpawn(command)
    frame_counter = thread.compile_pattern_list(
        [pexpect.EOF, "frame= *[0-9]+", "(.+)"])

    thread.compile_pattern_list([pexpect.EOF, "NUMBER_OF_FRAMES"])

    while True:
        sleep(1)
        result = thread.expect_list(frame_counter, timeout=10)
        if result == 0:
            # Reaches here only when the process has ended. Breaking out of the loop.
            break
        elif result == 1:
            # Getting the total number of frames processed.
            count = search('[0-9]+', (str(thread.match.group(0)))).group()
            animated_progress(int(count), frame_count,
                              int(time()) - start_time)

    return True, flac_file


if __name__ == '__main__':
    # A (fancy) welcome message, because why not
    #
    # ╮(╯▽╰)╭
    welcome_message: str = \
        """
             ____  __     __    ___       ___  ____  __ _  ____  ____   __  ____  __  ____
            (  __)(  )   / _\  / __)     / __)(  __)(  ( \(  __)(  _ \ / _\(_  _)/  \(  _ \\
             ) _) / (_/\/    \( (__     ( (_ \ ) _) /    / ) _)  )   //    \ )( (  O ))   /
            (__)  \____/\_/\_/ \___)     \___/(____)\_)__)(____)(__\_)\_/\_/(__) \__/(__\_)
        """

    # Printing the welcome message at the start of the script.
    print(welcome_message)

    # If length of `symbol` string is more than 4 characters, trimming it down to 4 characters.
    symbol = symbol[:4] if len(symbol) > 4 else symbol

    # Ensuring that the number of progress bars is an integer as it will be multiplied to a string.
    progress_bar_count = int(progress_bar_count)

    # Emptying the list as an edge-case precaution.
    files = []

    # Flag indicating if the interactive mode is to be used or not. True by default - disabled if
    # user has passed command-line arguments.
    interactive_mode: bool = True

    root = getcwd()
    force_write = False

    pattern_root = r'^--root="?(.*)"?$'
    pattern_force_write = r'^--force(="?yes"?|="?no"?)?$'

    if len(argv):
        interactive_mode = False  # Disabling interactive mode.

        # If an input parameter has been passed, extracting valid values before running the script.
        # Skipping the first parameter since it is the name of the script, and not an argument.
        for argument in argv[1:]:
            if match(pattern_root, argument):
                root = search(pattern_root, argument).groups()[0]

                if not isdir(root):
                    # Force-stop if the path does not point to a valid directory.
                    print(f'''
                        Unexpected value for the root directory: `{root}`

                        Make sure that the path is valid and points to an existing directory
                    ''')

                    sys_exit()
            elif match(pattern_force_write, argument):
                # Extracting the pattern
                force_write = search(pattern_force_write, argument).groups()
                if force_write and force_write[0]:
                    # If a value has been supplied, checking if it is
                    force_write = force_write[0].strip('="')  # Strip off the optional values.
                    force_write = True if force_write == 'yes' else False
                else:
                    force_write = False
            else:
                # If an unexpected value is encountered, stop the script midway.
                print(f'Unexpected argument `{argument}`')
                sys_exit()

    print(f'\nCurrent root directory is: `{root}`')

    # Infinite loop - used only if the script is going for the interactive mode, and will be broken
    # from the inside.
    while interactive_mode:
        # Getting the path of the root directory from the user. This loop will be broken
        # only when the the user provides a valid input for the root directory.
        root = input('Hit enter to continue, or enter the full path of any directory that you wish '
                     'to use as the root directory: ').strip()

        if len(root) == 0:
            # Get the working directory if the user goes ahead with the default option.
            root = getcwd()

        if not isdir(root):
            print(f'\nEntered path `{root}` does not belong to a directory.')
        else:
            print(f'\n\nUsing "{root}" as the root directory.')
            break

    # Getting a list of all the files that are present inside the root directory.
    # This function will populate `files` which is a list of strings with each
    # string being the full path of a file found inside the root directory.
    get_file_list(root)

    # Displaying brief info.
    print(f'\n\nFound {len(files)} files in the directory.')

    if interactive_mode:
        # Asking if conflicting files are to be overwritten or not inside interactive mode.
        force_write: Union[bool, str, None] = None
        while len(files) > 0:
            # Infinite loop as long as files are found in the root directory. Will break out of this
            # loop when user selects one a valid option. This check is to ensure that the user
            # isn't asked to choose when no file could be found in the root directory.
            force_write = str(input('Force overwrite any file(s) in case of a conflict (yes/no)? '
                                    'Warning; This could lead to loss of data: ').strip()).lower()

            if force_write in ['true', 'yes']:
                force_write = True
                break
            elif force_write in ['false', 'no']:
                force_write = False
                break

    for i in range(len(files)):
        print(f'\n({i + 1}/{len(files)}) Processing file: {path.basename(files[i])}')

        result, file = generate_flac_file(files[i], overwrite=force_write)
        if result:
            # Once the flac file is created successfully, replacing the progress bar with a filled
            # one, and time remaining as zero - without this, the progress bar will remain stuck
            # near the end and another will be drawn for the next file - this might confuse some
            # users into thinking that the process failed.
            animated_progress(100, 100, 0)

            # Finally printing the success message.
            print(f'\n\tGenerated file "{file}" successfully')

    # Displaying a nice little disappearing animation.
    animated_exit()
