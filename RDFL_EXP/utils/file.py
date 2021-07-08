import os
import shutil


def recursive_chown(path, owner, group=None):
    """
    Recursively change the owner of all the files in a folder
    :param path: path of the top level directory
    :param owner: uuid or name of the user that should become the owner
    :param group: guid or name of the group of the user that should become the owner (optional)
    """
    for dir_path, dir_names, filenames in os.walk(path):
        shutil.chown(dir_path, owner)
        for filename in filenames:
            shutil.chown(os.path.join(dir_path, filename), owner, group=group)
# End def recursive_chown
