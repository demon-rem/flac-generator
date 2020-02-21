from os import getcwd, listdir
from os.path import isdir, isfile, join
from threading import Thread
from time import sleep
from typing import List

import ffmpeg

# This list will contain the full paths of all the files that are found and
# will be processed.
files = list()

# Lists containing the file extensions of the files that will be supported by this script.
# Extensions can be added or removed as required, but doing so may cause errors (for
# example if `.png` is added as a supported extension)
audio_files = ['wav', 'mp3']
video_files = ['mp4', 'mkv']
# Also, the lists do not contain `.flac` as a valid extension, this is done because converting
# flac file back to flac is just a useless process for most of the files.


# The title of the directory that is to be ignored. Use a blank string as the value if no
# directory is to be ignored.
ignore_dir: str = '.ignore'


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


if __name__ == '__main__':

    # A welcome message, cos why not    ╮(╯▽╰)╭
    welcome_message: str = \
        """
             ____  __     __    ___       ___  ____  __ _  ____  ____   __  ____  __  ____
            (  __)(  )   / _\  / __)     / __)(  __)(  ( \(  __)(  _ \ / _\(_  _)/  \(  _ \\
             ) _) / (_/\/    \( (__     ( (_ \ ) _) /    / ) _)  )   //    \ )( (  O ))   /
            (__)  \____/\_/\_/ \___)     \___/(____)\_)__)(____)(__\_)\_/\_/(__) \__/(__\_)
        """
    print(welcome_message)

    # Emptying the list as an edge-case precaution
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

    # Displaying a nice little disappearing animation while waiting for user input
    # before killing the script.
    animated_exit()
