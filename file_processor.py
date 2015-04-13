"""
Process single file
"""
import leveldb
import tempfile
import shutil
import ntpath
import logging
import os
import sys
from myutils import compute_hash
from myutils import random_name

class FileProcessor(object):
    HASH_SEPARATOR = '@'
    FILE_PATH_MARK = ''
    ENCRYPTED_FILE_MARK = '#'

    def __init__(self, config, db, encryptor):
        self.database = db
        self.dropbox_folder = os.path.join(config.get('DropBox', \
            'drop_box_dir'), '')
        self.password = config.get('Credentials', 'password')
        self.logger = logging.getLogger("mylog")
        self.encryptor = encryptor

    def process(self, file_path):
        """
        Process single file
        """
        self.logger.info('Processing '+file_path)
        file_path_aug = file_path + self.FILE_PATH_MARK
        current_hash_of_unenc_file = ''
        try:
            current_hash_of_unenc_file = compute_hash(file_path)
            existing_combined_hash = self.database.Get(file_path_aug)
            split = existing_combined_hash.split(self.HASH_SEPARATOR)
            previous_hash_of_unenc_file = split[0]
            name = split[2]

            if previous_hash_of_unenc_file != current_hash_of_unenc_file:
                self.logger.info('File needs to be updated. Adding to dropbox' +
                    ' folder')
                self.__encrypt_copy(file_path, current_hash_of_unenc_file, name)
                self.logger.debug('Done')
            else:
                self.logger.info('File is up to date')

        except KeyError:
            self.logger.info('File not know. Adding to dropbox folder')
            self.__encrypt_copy(file_path, current_hash_of_unenc_file)
            self.logger.debug('Done')

    def __encrypt_copy(self, file_path, current_hash_of_unenc_file, name = None):
        """
        Encrypt file and copy to dropbox folder
        """

        self.logger.debug('Calling __encrypt_copy, file_path: ' + file_path +
            ' current_hash_of_unenc_file: ' + current_hash_of_unenc_file +
            ' name: ' + str(name))

        file_name = ntpath.basename(file_path)
        temp_dir = tempfile.gettempdir()
        temp_dir += '/'
        destination_path = temp_dir+file_name
        self.logger.debug('Temp destination: ' + destination_path)

        try:
            self.logger.debug('Copying ' + file_path + ' to '+
                destination_path)
            shutil.copy2(file_path, destination_path)
        except IOError:
            self.logger.error('Error copying ' + file_path + ' to '+
                destination_path)
            sys.exit()

        self.logger.debug('Encrypting ' + destination_path)
        #Encryptor returns the path with file name of encrypted file
        old_path = destination_path
        destination_path = self.encryptor(self.password, destination_path)
        self.logger.debug('Done...')
        #Remove original file (before encryption)
        os.remove(old_path)

        random_file_name = ''
        if name is None:
            random_file_name = random_name()
        else:
            random_file_name = name

        random_file_name_with_path = temp_dir + random_file_name

        try:
            self.logger.debug('Renaming ' + destination_path + ' to '
            +random_file_name_with_path)
            os.rename(destination_path, random_file_name_with_path)
        except OSError:
            self.logger.error('Error renaming ' + destination_path
                + ' to ' + random_file_name_with_path)
            sys.exit()

        current_hash_of_enc_file = compute_hash(random_file_name_with_path)
        combined_hash = current_hash_of_unenc_file
        combined_hash += self.HASH_SEPARATOR
        combined_hash += current_hash_of_enc_file
        combined_hash += self.HASH_SEPARATOR
        combined_hash += random_file_name
        batch = leveldb.WriteBatch()
        file_path_aug = file_path + self.FILE_PATH_MARK

        self.logger.debug('Insert in db: ' + file_path_aug + ' -> '+
            combined_hash)
        batch.Put(file_path_aug, combined_hash)

        self.logger.debug('Moving ' + random_file_name_with_path + ' to '
            + self.dropbox_folder)

        #Remove existing file
        if  os.path.isfile(self.dropbox_folder + random_file_name):
            self.logger.info('Removing file ' + self.dropbox_folder +
                random_file_name + ' from dropbox dir')
            try:
                os.remove(self.dropbox_folder + random_file_name)
            except OSError:
                self.logger.error('Error removing ' + self.dropbox_folder +
                    random_file_name)
                sys.exit()

        try:
            shutil.move(random_file_name_with_path, self.dropbox_folder +
                random_file_name)
        except IOError:
            self.logger.error('Error moving ' + random_file_name_with_path +
                ' to ' + self.dropbox_folder + random_file_name)
            sys.exit()
        self.database.Write(batch, sync=True)
