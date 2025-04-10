"""Handles downloading, patching and installation of the game files."""

import bz2
import concurrent.futures
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


class Patcher:
    """Game files patcher class for the launcher."""

    def __init__(self, debug=False):
        """Initialize the patcher with available download mirrors."""

        self.debug = False
        if debug:
            self.debug = True

        self.cpus = os.cpu_count()
        self.session = requests.Session()
        self.request_timeout = 30
        self.mirrors = None
        self.retry_count = 3
        self.retry_timeout = 10
        try:
            self.mirrors = helper.retry(
                self.retry_count, self.retry_timeout, self.__get_mirrors)
        except requests.exceptions.RequestException:
            print(
                '\nCould not get the download mirrors. '
                'Please check your internet connection '
                'as well as https://toon.town/status')
        except (json.decoder.JSONDecodeError, KeyError):
            print(
                '\nCould not decode the mirrors list. '
                "It's possible that there is a problem with "
                'the remote server. Please try again later.')

    def __get_mirrors(self):
        """Gets available download mirrors.

        :return: The mirror URLs.
        """

        mirror_url = 'https://www.toontownrewritten.com/api/mirrors'
        mirrors = self.session.get(
            url=mirror_url, timeout=self.request_timeout)
        mirrors.raise_for_status()
        mirrors = mirrors.json()
        random.shuffle(mirrors)

        return mirrors

    def __check_install_path(self, ttr_dir):
        """Checks if the installation path exists.
        Asks user to create the directory if it does not exist.

        :param ttr_dir: The currently set installation path in launcher.json.
        """

        if not os.path.exists(ttr_dir):
            ttr_dir_abs = os.path.abspath(ttr_dir)
            print(f'The path {ttr_dir_abs} does not exist. Create it?')
            answer = helper.confirm(
                'Enter 1 to confirm or 0 to cancel: ', 0, 1)

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

    def __patch_worker(self, ttr_dir, patch_manifest):
        """Runs the patching process for Toontown Rewritten.

        :param ttr_dir: The currently set installation path in launcher.json.
        :param patch_manifest: The patch manifest URL path.
        :return: True on success, False on failure.
        """

        system = self.__get_system()
        if system is not None:
            # Supported system detected
            # Download the patch manifest and load it as a json object
            try:
                patch_manifest = helper.retry(
                    self.retry_count, self.retry_timeout,
                    self.__get_patch_manifest,
                    patch_manifest=patch_manifest)
            except requests.exceptions.RequestException:
                print(
                    '\nCould not download the patch manifest. '
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
            return self.__check_files(ttr_dir, system, patch_manifest)

        # Not supported so display a message to the user
        print(
            '\nIt appears that your system is not compatible with '
            'Toontown Rewritten. If this is wrong please let me know!')

        return False

    def __get_system(self):
        """Checks if TTR is supported on the system.

        :return: The system name or None if system is not supported.
        """

        supported_systems = ['darwin', 'linux', 'linux2', 'win32', 'win64']
        system = sys.platform
        if platform.system() == 'Windows':
            system = 'win32'
            if platform.machine().endswith('64'):
                system = 'win64'

        if system not in supported_systems:
            system = None

        return system

    def __get_patch_manifest(self, patch_manifest):
        """Downloads the Toontown Rewritten patch manifest and stores as
        json object.

        :param patch_manifest: The patch manifest URL path.
        :return: The patch manifest as a json object
        """

        if patch_manifest.endswith('patchmanifest'):
            patch_manifest += '.txt'

        remote_file = f'https://cdn.toontownrewritten.com{patch_manifest}'
        request = self.session.get(
            url=remote_file, timeout=self.request_timeout)
        request.raise_for_status()
        patch_manifest = request.json()

        return patch_manifest

    def __check_files(self, ttr_dir, system, patch_manifest):
        """Check the local game files against the files in the patch manifest.
        For any files that don't exist locally, download the full file fresh.
        For files that do exist locally, check if it needs to be updated.

        :param ttr_dir: The currently set installation path in launcher.json.
        :param system: The system we are running on.
        :param patch_manifest: The patch manifest as a json object.
        :return: True on success, False on failure.
        """

        # Stores dictionary of the downloads to process
        download_info = {}

        # Check each file in the patch_manifest
        for filename in patch_manifest:
            # Get the absolute path to the file
            abs_file = os.path.join(ttr_dir, filename)

            # Get the download info for the file
            if not self.__check_patch(
                    system, abs_file, patch_manifest, download_info):
                return False

        if self.debug:
            print(f'DEBUG: download_info = {download_info}')

        if download_info:
            # New downloads were found
            return self.__download_worker(ttr_dir, download_info)

        # No new downloads were found
        return True

    def __check_patch(self, system, file, patch_manifest, download_info):
        """Checks if there is a patch for the specified file. If the file
        cannot be found on disk, assume it to be a new download request.

        :param system: The system we are running on.
        :param file: The absolute path of the file to patch check.
        :param patch_manifest: The patch manifest as a json object.
        :param download_info:
            Used to append additional downloads to an existing download_info
            dict. The format is shown below. Please note that the
            post_patch_hash key is only available for type => 'patch'.

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

        try:
            # Using the filename as the index in patch manifest, look for patch
            if (filename in patch_manifest
                    and system in patch_manifest[filename]['only']):
                with open(file, 'rb') as file_obj:
                    sha1sum = self.__get_sha1sum(file_obj)
                # File found in patch_manifest, check if hash matches
                if self.debug:
                    print(f'DEBUG: {filename} local hash: {sha1sum}')
                    print(
                        f'DEBUG: {filename} remote hash: '
                        f'{patch_manifest[filename]["hash"]}')

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

                        if self.debug:
                            print(f'DEBUG: Patch found for {filename}')
                    else:
                        # Patch not found, add as a full download
                        download_info_new = {
                            patch_manifest[filename]['dl']: {
                                'type': 'full',
                                'local_filename': filename,
                                'hash': patch_manifest[filename]['hash'],
                                'comp_hash': patch_manifest[
                                    filename]['compHash']
                            }
                        }

                        if self.debug:
                            print(f'DEBUG: Patch not found for {filename}')
                else:
                    # Hash matches, file is already up to date
                    if self.debug:
                        print(f'DEBUG: {filename} is already up to date')
        except FileNotFoundError:
            if self.debug:
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

    def __get_sha1sum(self, file_obj):
        """Hashes and returns sha1sum of the contents of a file object.

        :param file_obj: The file object.
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

    def __download_worker(self, ttr_dir, download_info):
        """Prepares the download by requesting a download mirror endpoint and
        sets up a temporary directory for staging. Downloads are then
        decompressed and processed.

        :param ttr_dir: The currently set installation path in launcher.json.
        :param download_info: The download info dictionary.
        :return: True on success, False on failure.
        """

        if self.mirrors is None:
            # Cancel the download since no mirrors could be found
            return False

        try:
            # Create a temporary directory to stage the downloads
            with tempfile.TemporaryDirectory(dir=ttr_dir) as temp:
                # Locate where the temporary directory is
                temp_dir = os.path.join(tempfile.gettempdir(), temp)

                # Build list of params for downloads
                download_file_params = []
                for filename in download_info:
                    # Files to download
                    download_file_params.append(
                        (ttr_dir, temp_dir, download_info[filename],
                            filename, self.mirrors))

                # Download files
                with concurrent.futures.ThreadPoolExecutor(
                        max_workers=self.cpus) as executor:
                    futures = [executor.submit(
                        self.__attempt_download_file,
                        i[0], i[1], i[2], i[3], i[4]
                        ) for i in download_file_params]

                # Check for any failed downloads
                for future in concurrent.futures.as_completed(futures):
                    if not future.result():
                        print(
                            '\nOne or more downloads failed. '
                            'Please try again in a few minutes.')
                        return False
        except FileNotFoundError:
            print('\nFailed to create temporary directory.')
            return False

        return True

    def __attempt_download_file(
            self, ttr_dir, temp_dir, file_info, remote_filename, mirrors):
        """Wrapper for __download_file. Used for attempting and retrying a
        failed download.

        :param ttr_dir: The currently set installation path in launcher.json.
        :param temp_dir: The temporary directory to download files to.
        :param file_info: The file info dictionary.
        :param remote_filename: The file to download.
        :param mirrors: The list of download mirrors.
        :return: True on success, False on failure.
        """

        return helper.retry(
            self.retry_count, self.retry_timeout, self.__download_file,
            False, ttr_dir=ttr_dir, temp_dir=temp_dir, file_info=file_info,
            remote_filename=remote_filename, mirrors=mirrors)

    def __download_file(
            self, ttr_dir, temp_dir, file_info, remote_filename, mirrors):
        """Downloads a file from a mirror.

        :param ttr_dir: The currently set installation path in launcher.json.
        :param temp_dir: The temporary directory to download files to.
        :param file_info: The file info dictionary.
        :param remote_filename: The file to download.
        :param mirrors: The list of download mirrors.
        :return: True on success, False on failure.
        """

        mirror = mirrors[0]
        local_filename = file_info['local_filename']
        comp_hash = file_info['comp_hash']
        decomp_file_path = os.path.join(temp_dir, local_filename)
        decomp_hash = file_info['hash']
        chunk_size = 65536

        # Attempt to download the file
        try:
            response = requests.get(
                url=urljoin(mirror, remote_filename),
                timeout=self.request_timeout, stream=True)
            response.raise_for_status()

            # Open temporary file for writing
            temp_file_path = os.path.join(temp_dir, remote_filename)
            with open(temp_file_path, 'w+b') as comp_file:
                # Display progress of writing the file with tqdm
                with tqdm.wrapattr(
                        comp_file, 'write',
                        total=int(response.headers.get('Content-Length')),
                        unit='B', unit_scale=True,
                        desc=f'Downloading {local_filename}', leave=False,
                        ascii=' █') as fobj:
                    # Write to the file in chunks
                    for chunk in response.iter_content(
                            chunk_size=chunk_size):
                        fobj.write(chunk)

            # Verify downloaded file hash
            with open(temp_file_path, 'rb') as comp_file:
                local_comp_hash = self.__get_sha1sum(comp_file)
                if local_comp_hash != comp_hash:
                    # Hash mismatch, fail the download
                    return False

            # Decompress file
            res = self.__decompress_bz2(
                temp_file_path, decomp_file_path, decomp_hash)
            if not res:
                return False

            # Process decompressed file
            res = self.__process_decompressed_file(
                ttr_dir, temp_dir, file_info)
            if not res:
                return False
        except (FileNotFoundError, requests.exceptions.RequestException):
            if len(mirrors) > 1:
                mirrors.remove(mirror)

            return False

        return True

    def __decompress_bz2(self, comp_file_path, decomp_file_path, decomp_hash):
        """Decompress the downloaded bz2 file more efficiently.

        :param comp_file_path: The path to the compressed file.
        :param decomp_file_path: The path the decompressed file will be
                                 written to.
        :param decomp_hash: The hash to verify the decompress file.
        :return: True on success, False on failure.
        """

        chunk_size = 65536
        comp_file_size = os.path.getsize(comp_file_path)
        filename = os.path.basename(comp_file_path)

        with bz2.BZ2File(comp_file_path, 'rb') as comp_file:
            with open(decomp_file_path, 'wb') as decomp_file:
                with tqdm(
                        total=comp_file_size, unit='B', unit_scale=True,
                        desc=f'Decompressing {filename}',
                        leave=False, ascii=' █') as pbar:
                    while True:
                        data = comp_file.read(chunk_size)
                        if not data:
                            break
                        decomp_file.write(data)
                        pbar.update(len(data))

        # Verify decompressed file hash
        with open(decomp_file_path, 'rb') as decomp_file:
            local_decomp_hash = self.__get_sha1sum(decomp_file)
            if local_decomp_hash != decomp_hash:
                # Hash mismatch, something went wrong with decompression
                print(f'\nFailed to decompress {filename}.')
                return False

        return True

    def __process_decompressed_file(self, ttr_dir, temp_dir, file_info):
        """Processes the decompressed download. Full downloads are moved into
        the TTR directory while patches are applied to existing files using
        bsdiff4.

        :param ttr_dir: The currently set installation path in launcher.json.
        :param temp_dir: The temporary directory to download files to.
        :param file_info: The file info dictionary.
        :return: True on success, False on failure.
        """

        dl_type = file_info['type']
        local_filename = file_info['local_filename']
        temp_file_path = os.path.join(temp_dir, local_filename)
        final_file_path = os.path.join(ttr_dir, local_filename)

        if dl_type == 'full':
            # Move decompressed file to install directory
            shutil.move(temp_file_path, final_file_path)
        elif dl_type == 'patch':
            # Apply the bsdiff4 patch inplace
            bsdiff4.file_patch_inplace(final_file_path, temp_file_path)

            # Verify patch was applied successfully by comparing hashes
            with open(final_file_path, 'rb') as final_file:
                post_patch_hash = file_info['post_patch_hash']
                local_post_patch_hash = self.__get_sha1sum(final_file)
                if local_post_patch_hash != post_patch_hash:
                    # Hash mismatch, something went wrong with the patch
                    print(f'\nFailed to apply patch to {local_filename}')
                    return False

        return True

    def check_update(self, ttr_dir, patch_manifest):
        """Checks for updates for Toontown Rewritten and installs them.

        :param ttr_dir: The currently set installation path in launcher.json.
        :param patch_manifest: The patch manifest URL path.
        :return: True on success, False if user declines or on failure.
        """

        # Check if TTR installation directory exists
        if not self.__check_install_path(ttr_dir):
            return False

        # Downloads and installs any new game files
        if not self.__patch_worker(ttr_dir, patch_manifest):
            return False

        return True
