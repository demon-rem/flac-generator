from os import getcwd, listdir, path
from os.path import isdir, isfile, join
from threading import Thread
from time import sleep, time
from typing import List
from re import search

import pexpect
from pexpect import popen_spawn

# This list will contain the full paths of all the files that are found and
# will be processed.
files = list()

# Lists containing the file extensions of the files that will be supported by this script.
# Extensions can be added or removed as required, but doing so may cause errors (for
# example if `.png` is added as a supported extension)
audio_files = ['wav', 'mp3']
video_files = ['mp4', 'mkv']
# Also, these lists do not contain `flac` as a valid extension, why will anyone want
# to generate a flac file from a flac file :p


# The title of the directory that is to be ignored. Use a blank string as the value if no
# directory is to be ignored.
ignore_dir: str = '.ignore'

# The total number of progress bars (hashes by default) present in the progress bar.
progress_bar_count: int = 30

# The symbol that is used to generate the progress bar. Max length of 4 characters.
symbol: str = '#'


def get_file_list(root: str, mode: str = 'recursive') -> None:
    """
        Returns a list of strings, each of these strings contains the full path
        of a file present inside the given location directory.


        Parameters
        -----------
        root:
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
        None. Each file found will be appended to the global `files` list from where it can be
        retrived by the calling function once the execution of this function ends.
    """

    if not isdir(root):
        raise FileNotFoundError(f'The directory "{root}" does not exist')

    items = listdir(root)

    for item in items:
        # Appending all the files of the supported types to the list of files found.
        item: str = join(root, item)
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

            item = join(root, item)
            if isdir(item):
                get_file_list(item, mode)

    return files


def animated_exit() -> None:
    """
        Implements a nice little animation while waiting for the user to give an input
        to the script.

        Remarks
        --------
        This function is designed to be used to get user input only before the script quits.

        Once the user gives an input to this method, the script will be force killed by this
        method

        {{{(>_<)}}}
    """

    # Adding some vertical spacing to make sure that the animated effect is not
    # lost in a sea of text.
    print('\n\n\n')

    take_input: bool = False
    thread: Thread = None
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

        # If the thread is dead, it signifies that the user has entered an input,
        # killing the script.
        if not thread.isAlive():
            exit(0)


def print_time(seconds: int) -> str:
    """
        Converts a given number of seconds into a human-understandable format and return the result
        as a string.

        Parameters
        -----------
        seconds:
            An integer containing the amount of seconds. Should be an integer greater than zero\n

        Exceptions
        -----------
        TypeError: Thrown if the parameter isn't an integer\n
        ValueError: Thrown if the argument passed is less than zero\n

        Returns
        --------
        String containing the amount of time in readable format.
    """

    if not isinstance(seconds, int):
        raise TypeError(f'The value of `seconds` should be an integer.')
    elif seconds < 0:
        raise ValueError(f'Value of `seconds` too low [{seconds}]')

    # The list contains strings that will be used as units of time in reversed order.
    units: List[str] = [
        'weeks',
        'days',
        'hours',
        'minutes',
        'seconds'
    ]

    # Creating list to store amount of time. Attaching the list to the method
    # object, this way these values won't be calculated every time this method
    # is called (saving some processing power). This is an ugly-hack to use
    # `static` variables inside a method directly. The values will be calculated
    # only once when the function is run first time.
    print_time.time_units: List[int] = [
        60 * 60 * 24 * 7,   # Weeks
        60 * 60 * 24,       # Days
        60 * 60,            # Hours
        60,                 # Minutes
        1                   # Seconds
    ]

    result: str = ''
    index: int = 0

    while (min([len(print_time.time_units), len(units)]) > index):
        if seconds >= print_time.time_units[index]:
            cal = int(seconds / print_time.time_units[index])
            result += str(cal) + ' ' + units[index] + ' '
            seconds %= print_time.time_units[index]
        index += 1

    return result.strip()


def animated_progress(frame_count: int, total_frames: int, time_elapsed: int) -> None:
    """
        Prints a progress bar to the screen.

        Parameters
        -----------
        frame_count:
            An integer containing the number of frames that have been currently processed.
            Should be less than or equal to `total_frames` and greater than or equal to zero\n
        total_frames:
            An integer containing the total number of frames. Will be used to calculate the current
            progress and the estimated time remaining\n
        time_elapsed:
            An integer containing the count of seconds elapsed before reaching this frame since the
            processing of the current file started, should be a positive integer. Used to calculate ETA\n

        Exceptions
        -----------
        TypeError: Thrown if any of the variables is not an integer\n
        ValueError: Thrown if any of the arguments is less than zero, or is `total_frames` is
            zero, or if value of `frame_count` is greater than the value of `total_frames`\n
    """

    if not isinstance(frame_count, int) or not isinstance(total_frames, int) or \
            not isinstance(time_elapsed, int):
        raise Exception.TypeError('Non-integer argument supplied.')
    elif frame_count < 0:
        raise ValueError(f'Frame count [{frame_count}] can\'t be negative')
    elif total_frames <= 0:
        raise ValueError(f'Total frames [{total_frames}] too less.')
    elif frame_count > total_frames:
        raise ValueError(f'Current frame count [{frame_count}] cannot be greater '
                         'than total frame count [{total_frames}]')
    elif time_elapsed < 0:
        raise ValueError(f'Time elapsed [{time_elapsed}] can\'t be negative')

    # The progress will be shown with a progress bar, each 'hash' symbol in the bar representing a fixed
    # percentage of progress.
    percentage: float = round(float(frame_count/total_frames) * 100, 3)

    # Calculating the number of seconds remaining to complete. Calculating this as the number of frames
    # being processed in a single second, divided by the total number of frames.
    eta: int = int(total_frames / float(frame_count / time_elapsed))

    # The value of `eta` right now is the amount of seconds required to process the entire file
    # from beginning. But, a certain amount of time has already elapsed. Removing that time
    # to get the time remaining.
    eta = eta - time_elapsed

    hashes: int = int(percentage * progress_bar_count / 100)
    print(f'\t{percentage}%', (symbol * hashes) + (' ' * (progress_bar_count - hashes)),
          f'Remaining: {print_time(eta)}', sep='\t ', end='\t\t\t\r')


def generate_flac_file(original_file: str, *, force_write: bool = False) -> bool:
    """
        The main method that will generate the flac file and save it in the destination directory
        as required.

        Remarks
        --------
        This function will simply take in the original file that is to be converted into a flac file,
        use ffmpeg in the backend to generate a flac file with the same name as the original
        file and subsequently save the file in the same directory as the original file.

        Since this function handles the most important task of this script, this function also has the
        highest probability of an unexpected failure/crash.

        *Realizes that deleting this method will leave bug-free code*

        (╯°□°）╯︵ ┻━┻

        Exceptions
        -----------
        OSError.FileNotFoundError: Thrown if the path supplied for the original file is invalid or if the
            path points to a directory instead of a file.

        Parameters
        -----------
        original_file:
            A string containing the full file path of the original file which is to be converted to
            a flac file\n
        force_write:
            Boolean indicating if the file is already existing, should it be overwritten or not.
            Default --> false\n

        Returns
        --------
        True if the flac file was generated successfully, false in case of any error.

        If any error occurs, the message will be printed directly to the screen by this method,
        the part of returning the error message to the calling function is not required.
    """

    if not isfile(original_file):
        raise FileNotFoundError(f'No file found at the path "{original_file}"')

    # Getting the directory in which the original file is stored, creating a new
    # path for the flac file using the location and the name of the original file
    # and changing the extension of the original file.
    directory, file_name = path.split(original_file)
    flac_file = join(directory, file_name.rpartition('.')[0]) + '.flac'

    # Firing a blank input at ffmpeg to get the number of frames present in the file.
    # Doing this will result in a warning (since ffmpeg is not made to be used to get
    # file info) -- `ffprobe` can be used as an alternative for this purpose, however
    # not everyone will be willing to keep ffprobe just for this reason, so going with
    # this hack-y approach to get the number of frames in the video.
    info_command = f'ffmpeg.exe -i "{original_file}"'
    thread = popen_spawn.PopenSpawn(info_command)

    # Once the process finishes, getting the result from the command.
    output = str(thread.read())

    # Using string splitting over regex to get the frame count from the output.
    # This way certainly seems a lot more readable to me than regex (¬_¬")
    frame_count = int(output.split('NUMBER_OF_FRAMES-', 1)[-1]
                      .split('\\r', 1)[0].strip().split(' ', 1)[-1].strip())

    # Creating a string for all the arguments that will be used along with
    # the ffmpeg base command.
    command = f'ffmpeg.exe -i "{original_file.strip()}" -c:a flac "{flac_file.strip()}"'

    if force_write:
        # If existing files are to be overwritten, appending '-y' to ffmpeg command. This will
        # be used if a clash occurs (i.e. a file with the same name as `flac_file` already exists).
        command += ' -y'

    # Getting the start time before firing the process.
    start_time: int = int(time())

    # Creating a process that uses ffmpeg along the with the parameters to generate a
    # flac file.
    thread = popen_spawn.PopenSpawn(command)
    frame_counter = thread.compile_pattern_list(
        [pexpect.EOF, "frame= *[0-9]+", "(.+)"])

    frame_info = thread.compile_pattern_list([pexpect.EOF, "NUMBER_OF_FRAMES"])

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

    return True


if __name__ == '__main__':
    # A (fancy) welcome message, cos why not    ╮(╯▽╰)╭
    welcome_message: str = \
        """
             ____  __     __    ___       ___  ____  __ _  ____  ____   __  ____  __  ____
            (  __)(  )   / _\  / __)     / __)(  __)(  ( \(  __)(  _ \ / _\(_  _)/  \(  _ \\
             ) _) / (_/\/    \( (__     ( (_ \ ) _) /    / ) _)  )   //    \ )( (  O ))   /
            (__)  \____/\_/\_/ \___)     \___/(____)\_)__)(____)(__\_)\_/\_/(__) \__/(__\_)
        """
    print(welcome_message)

    # If length of `symbol` string is more than 4 characters, trimming it down to 4 characters.
    symbol = symbol[:4] if len(symbol) > 4 else symbol

    # Ensuring that the number of progress bars is an integer as it will be multiplied to a string.
    progress_bar_count = int(progress_bar_count)

    # Emptying the list as an edge-case precaution.
    files = []

    print(f'\nCurrent root directory is `{getcwd()}`')

    while True:
        # Getting the path of the root directory from the user. This loop will be broken
        # only when the the user provides a valid input for the root directory.
        root = input('Hit enter to continue, or enter the full path of any directory ' +
                     'that you wish to use as the root directory: ').strip()

        if len(root) == 0:
            root = getcwd()

        if not isdir(root):
            print(f'\nEntered path `{root}` does not belong to a directory.')
        else:
            print(f'\n\nUsing {root} as the root directory.')
            break

    # Getting a list of all the files that are present inside the root directory.
    # This function will populate `files` which is a list of strings with each
    # string being the full path of a file found inside the root directory.
    get_file_list(root)

    # Displaying brief info.
    print(f'\n\nFound {len(files)} files in the directory.')

    # Asking if conflicting files are to be overwritten or not.
    choice: bool = None
    while True:
        choice = str(input('Force overwrite any file(s) in case of a conflict (yes/no)? '
                           'Warning; This could result in a loss of data: ').strip()).lower()

        if choice in ['true', 'yes']:
            choice = True
            break
        elif choice in ['false', 'no']:
            choice = False
            break

    # Displaying a nice little disappearing animation while waiting for user input
    # before killing the script.
    animated_exit()
