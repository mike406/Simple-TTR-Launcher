#!/usr/bin/env python3

# Copyright (C) 2023 Michael Luck
# Distributed under the GNU GPL v3. For full terms see the file LICENSE.txt

# This file is part of Simple TTR Launcher.

# Simple TTR Launcher is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Simple TTR Launcher is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Simple TTR Launcher. If not, see <http://www.gnu.org/licenses/>.

"""Handles downloading, patching and installation of the game files."""

import bz2
import hashlib
import json
import os
import platform
import random
import shutil
import sys
import tempfile
from urllib.parse import urljoin
import bsdiff4
import requests
from tqdm.auto import tqdm
import helper


def check_update(ttr_dir):
    """Checks for updates for Toontown Rewritten and installs them.

    :param ttr_dir: The currently set installation path in login.json.
    :return: True on success, False if user declines or on failure.
    """

    # Check if TTR installation directory exists
    if not check_install_path(ttr_dir):
        return False

    # Downloads and installs any new game files
    if not patch_worker(ttr_dir):
        return False

    return True


def check_install_path(ttr_dir):
    """Checks if the installation path exists.
    Asks user to create the directory if it does not exist.

    :param ttr_dir: The currently set installation path in login.json.
    """

    if not os.path.exists(ttr_dir):
        ttr_dir_abs = os.path.abspath(ttr_dir)
        print(f'The path {ttr_dir_abs} does not exist. Create it?')
        answer = helper.confirm(
            'Enter 1 to confirm or 0 for Main Menu: ', 0, 1)

        if answer == 1:
            try:
                os.makedirs(ttr_dir)
            except OSError:
                print(
                    '\nFailed to create directory.\n'
                    'Ensure you have permission to write to the '
                    f'path specified: {ttr_dir_abs}')

                return False
        else:
            return False

    return True


def patch_worker(ttr_dir):
    """Runs the patching process for Toontown Rewritten.

    :param ttr_dir: The currently set installation path in login.json.
    :return: True on success, False on failure.
    """

    system = get_platform()
    if system is not None:
        # Supported platform detected
        # Download the patch manifest and load it as a json object
        try:
            patch_manifest = helper.retry(
                3, 5, get_patch_manifest)
        except requests.exceptions.RequestException:
            print(
                '\nCould not download the patch manifest '
                'Please check your internet connection '
                'as well as https://toon.town/status')

            return False
        except json.decoder.JSONDecodeError:
            print(
                '\nCould not decode the patch manifest. '
                "It's possible that there is a problem with "
                'the remote server. Please try again later.')

            return False

        # Now that we have the patch manifest we can start comparing
        # the file list to the files in the local install path
        return check_files(ttr_dir, patch_manifest)

    # Not supported so display a message to the user
    print(
        '\nIt appears that your system is not compatible with '
        'Toontown Rewritten. If this is wrong please let me know!')

    return False


def get_platform():
    """Checks if TTR is supported on the system.

    :return: The platform name or None if system is not supported.
    """

    supported_dist = ['darwin', 'linux', 'linux2', 'win32', 'win64']
    if platform.system() == 'Windows':
        if platform.machine().endswith('64'):
            dist = 'win64'
        else:
            dist = 'win32'
    else:
        dist = sys.platform

    if dist not in supported_dist:
        dist = None

    return dist


def get_patch_manifest():
    """Downloads the Toontown Rewritten patch manifest and stores as
    json object.

    :return: The patch manifest as a json object
    """

    remote_file = 'https://cdn.toontownrewritten.com/content/patchmanifest.txt'
    request = requests.get(url=remote_file, timeout=30)
    request.raise_for_status()
    patch_manifest = request.json()

    return patch_manifest


def check_files(ttr_dir, patch_manifest, debug=False):
    """Check the local game files against the files in the patch manifest.
    For any files that don't exist locally, download the full file fresh.
    For files that do exist locally, check if it needs to be updated.

    :param ttr_dir: The currently set installation path in login.json.
    :param patch_manifest: The patch manifest as a json object.
    :param debug: Set to True to print DEBUG messages.
    :return: True on success, False on failure.
    """

    # Stores dictionary of the downloads to process
    download_info = {}

    # Check each file in the patch_manifest
    for filename in patch_manifest:
        # Get the absolute path to the file
        abs_file = os.path.join(ttr_dir, filename)

        # Get the download info for the file
        if not check_patch(abs_file, patch_manifest, download_info):
            return False

    if debug:
        print(f'DEBUG: download_info = {download_info}')

    if download_info:
        # New downloads were found
        return prepare_download(ttr_dir, download_info)

    # No new downloads were found
    return True


def check_patch(file, patch_manifest, download_info, debug=False):
    """Checks if there is a patch for the specified file. If the file cannot
    be found on disk, assume it to be a new download request.

    :param file: The absolute path of the file to patch check.
    :param patch_manifest: The patch manifest as a json object.
    :param debug: Set to True to print DEBUG messages.
    :param download_info:
        Used to append additional downloads to an existing download_info dict.
        The format is shown below. Please note that the post_patch_hash key
        is only available for type => 'patch'.

        download_info = {
            'filename1': {
                'type': <'full' or 'patch'>,
                'local_filename': <filename to use for disk>,
                'hash': <hash after file is decompressed>,
                'comp_hash': <hash of the compressed downloaded file>,
                'post_patch_hash': <final hash after applying bsdiff patch>
            },
            'filename2': {
                'type': <'full' or 'patch'>,
                'local_filename': <filename to use for disk>,
                'hash': <hash after file is decompressed>,
                'comp_hash': <hash of the compressed downloaded file>,
                'post_patch_hash': <final hash after applying bsdiff patch>
            },
            'filenamex': {
                'type': <'full' or 'patch'>,
                'local_filename': <filename to use for disk>,
                'hash': <hash after file is decompressed>,
                'comp_hash': <hash of the compressed downloaded file>,
                'post_patch_hash': <final hash after applying bsdiff patch>
            }
        }
    :return: True on success, False on failure.
    """

    download_info_new = {}
    filename = os.path.basename(file)
    system = get_platform()

    try:
        # Using the filename as the index in patch manifest, look for a patch
        if (filename in patch_manifest
                and system in patch_manifest[filename]['only']):
            with open(file, 'rb') as file_obj:
                sha1sum = get_sha1sum(file_obj)
            # File found in patch_manifest, check if hash matches
            if debug:
                print(f'DEBUG: Local hash: {sha1sum}')
                print(
                    f'DEBUG: Remote hash: {patch_manifest[filename]["hash"]}')

            if sha1sum != patch_manifest[filename]['hash']:
                # Hash does not match, see if match is found in patches
                if sha1sum in patch_manifest[filename]['patches']:
                    # Patch found, add as a patch download
                    patch_filename = (
                        os.path.basename(
                            patch_manifest
                            [filename]['patches'][sha1sum]['filename']))
                    patch_hash = (
                        patch_manifest
                        [filename]['patches'][sha1sum]['patchHash'])
                    comp_patch_hash = (
                        patch_manifest
                        [filename]['patches'][sha1sum]['compPatchHash'])
                    post_patch_hash = patch_manifest[filename]['hash']

                    download_info_new = {
                        patch_filename: {
                            'type': 'patch',
                            'local_filename': filename,
                            'hash': patch_hash,
                            'comp_hash': comp_patch_hash,
                            'post_patch_hash': post_patch_hash
                        }
                    }

                    if debug:
                        print(f'DEBUG: Patch found for {filename}')
                else:
                    # Patch not found, add as a full download
                    download_info_new = {
                        patch_manifest[filename]['dl']: {
                            'type': 'full',
                            'local_filename': filename,
                            'hash': patch_manifest[filename]['hash'],
                            'comp_hash': patch_manifest[filename]['compHash']
                        }
                    }

                    if debug:
                        print(f'DEBUG: Patch not found for {filename}')
            else:
                # Hash matches, file is already up to date
                if debug:
                    print(f'DEBUG: {filename} is already up to date')
    except FileNotFoundError:
        if debug:
            print(f'DEBUG: {filename} will be downloaded in full.')

        # Could not find the file on disk, add as a full download
        try:
            download_info_new = {
                patch_manifest[filename]['dl']: {
                    'type': 'full',
                    'local_filename': filename,
                    'hash': patch_manifest[filename]['hash'],
                    'comp_hash': patch_manifest[filename]['compHash']
                }
            }
        except KeyError:
            # Under normal circumstances this shouldn't happen, but if
            # we encounter a file not in the patch manifiest just ignore it
            pass

    download_info.update(download_info_new)
    return True


def get_sha1sum(file_obj):
    """Hashes and returns sha1sum of the contents of a file object.

    :param file: The file object.
    :return: The sha1sum of the file.
    """

    chunk_size = 65536
    sha1 = hashlib.sha1()

    file_obj.seek(0)
    while True:
        data = file_obj.read(chunk_size)
        if not data:
            break
        sha1.update(data)

    return sha1.hexdigest()


def prepare_download(ttr_dir, download_info):
    """Prepares the download by requesting a download mirror endpoint and sets
    up a temporary directory for staging.

    :param ttr_dir: The currently set installation path in login.json.
    :param download_info: The download info dictionary.
    :return: True on success, False on failure.
    """

    # Choose a download mirror
    try:
        mirror = helper.retry(
            3, 5, get_mirror)
    except requests.exceptions.RequestException:
        print(
            '\nCould not get a download mirror. '
            'Please check your internet connection '
            'as well as https://toon.town/status')
        return False
    except (json.decoder.JSONDecodeError, KeyError):
        print(
            '\nCould not decode the mirrors list. '
            "It's possible that there is a problem with "
            'the remote server. Please try again later.')
        return False

    try:
        # Create a temporary directory to stage the downloads
        with tempfile.TemporaryDirectory() as temp:
            # Locate where the temporary directory is
            temp_root = tempfile.gettempdir()
            temp_dir = os.path.join(temp_root, temp)

            # Start processing each download
            bar_format = '{l_bar}{bar}| {n_fmt}/{total_fmt}'
            for filename in tqdm(
                        download_info,
                        desc='Update Progress',
                        bar_format=bar_format,
                        ascii=" █"
                    ):

                # Download the file
                result = helper.retry(
                    3, 5, download_file, ttr_dir=ttr_dir,
                    temp_dir=temp_dir, file_info=download_info[filename],
                    remote_filename=filename, mirror=mirror)

                # Download failed too many times
                if not result:
                    return False
    except FileNotFoundError:
        print('\nFailed to create temporary directory.')
        return False

    return True


def get_mirror():
    """Chooses a download mirror endpoint.

    :return: The mirror URL.
    """

    mirror_url = 'https://www.toontownrewritten.com/api/mirrors'
    mirrors = requests.get(url=mirror_url, timeout=30)
    mirrors.raise_for_status()
    mirror = random.choice(mirrors.json())

    return mirror


def download_file(ttr_dir, temp_dir, file_info, remote_filename, mirror):
    """Downloads a file from the mirror.

    :param ttr_dir: The currently set installation path in login.json.
    :param temp_dir: The temporary directory to download files to.
    :param file_info: The file info dictionary.
    :param remote_filename: The file to download.
    :param mirror: The download mirror.
    :return: True on success, False on failure.
    """

    local_filename = file_info['local_filename']
    chunk_size = 65536

    # Attempt to download the file
    try:
        with requests.get(
                    url=urljoin(mirror, remote_filename),
                    timeout=1,
                    stream=True
                ) as request:
            request.raise_for_status()

            # Open temporary file for writing
            temp_file_path = os.path.join(temp_dir, remote_filename)
            with open(temp_file_path, 'w+b') as comp_file:
                # Display progress of writing the file with tqdm
                with tqdm.wrapattr(
                            comp_file,
                            'write',
                            total=int(request.headers.get('Content-Length')),
                            desc=f'Downloading {local_filename}',
                            leave=False,
                            ascii=" █"
                        ) as fobj:

                    # Write to the file in chunks
                    for chunk in request.iter_content(chunk_size=chunk_size):
                        fobj.write(chunk)

                # Open file to write decompressed data to
                with open(
                            os.path.join(temp_dir, local_filename), 'w+b'
                        ) as decomp_file:
                    # Process the downloaded file and write its content
                    process_downloaded_file(
                        ttr_dir, comp_file, decomp_file, file_info)
    except RuntimeError:
        print(
            f'\nDownloaded file {local_filename} checksum did not match.')

        return False
    except (FileNotFoundError, requests.exceptions.RequestException):
        print(f'\nFailed to download {local_filename}.')

        return False

    return True


def process_downloaded_file(ttr_dir, comp_file, decomp_file, file_info):
    """Processes the downloaded file by decompressing the data and saving to
    the TTR installation directory.

    :param ttr_dir: The currently set installation path in login.json.
    :param comp_file: The downloaded compressed file as a file object.
    :param decomp_file: The writable file object for saving the decompressed
                        file.
    :param file_info: The file info dictionary.
    """

    dl_type = file_info['type']
    local_filename = file_info['local_filename']
    decomp_hash = file_info['hash']
    comp_hash = file_info['comp_hash']

    # Verify comp_hash
    local_comp_hash = get_sha1sum(comp_file)
    if local_comp_hash == comp_hash:
        # Hash is good, we can decompress the archive
        decompress_bz2(comp_file, decomp_file)

        # Verify decomp_hash
        local_hash = get_sha1sum(decomp_file)
        if local_hash == decomp_hash:
            # Hash is good, we can move the final file
            # If type is full just move the file, else apply as patch
            final_file_path = os.path.join(ttr_dir, local_filename)
            if dl_type == 'full':
                # Write decomp_file to install directory
                with open(final_file_path, 'w+b') as final_file:
                    decomp_file.seek(0)
                    final_file.seek(0)
                    shutil.copyfileobj(decomp_file, final_file)
            elif dl_type == 'patch':
                # Apply the bsdiff4 patch inplace
                post_patch_hash = file_info['post_patch_hash']
                bsdiff4.file_patch_inplace(final_file_path, decomp_file.name)

                # Verify patch was applied successfully by comparing hashes
                with open(final_file_path, 'rb') as final_file:
                    local_post_patch_hash = get_sha1sum(final_file)
                    if local_post_patch_hash != post_patch_hash:
                        raise RuntimeError
        else:
            # Hash mismatch, don't proceed any further
            raise RuntimeError
    else:
        # Hash mismatch, don't proceed any further
        raise RuntimeError


def decompress_bz2(comp_file, decomp_file):
    """Decompress the downloaded bz2 file.

    :param comp_file_path: The path to the compressed file.
    :param decomp_file_path: The path the decompressed file will be written to.
    """

    chunk_size = 65536

    decompressor = bz2.BZ2Decompressor()

    comp_file.seek(0)
    while True:
        data = comp_file.read(chunk_size)
        if not data:
            break
        decomp_file.write(decompressor.decompress(data))
