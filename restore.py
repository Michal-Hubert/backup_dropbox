'''
Restoring module
'''
import logging
import os
import shutil
import getpass
import tarfile
import leveldb
import ntpath
import backup
from myutils import decrypt_file, path_leaf
from ConfigParser import SafeConfigParser
from file_processor import FileProcessor

def restore(dropbox_path, destiantion, override):
    '''
    Restoring module
    dropbox_path: direcotry of dropbox_path
    destiantion: directory where database shall be put
    '''
    logger = logging.getLogger('mylog')
    db_in_dropbox = os.path.join(dropbox_path, '') + backup.META_DB_NAME + \
    '.xyz'
    db_destination = os.path.join(destiantion, '') + backup.META_DB_NAME + \
    '.xyz'
    logger.info('DB restoring from ' + db_in_dropbox + ' to ' + db_destination)

    logger.debug('Copying ' + db_in_dropbox + ' to ' + db_destination)
    shutil.copy2(db_in_dropbox, db_destination)

    password = getpass.getpass()
    decrypt_file(password, db_destination)

    tar = tarfile.open(os.path.join(destiantion, '') + backup.META_DB_NAME)
    tar.extractall(path=os.path.join(destiantion, ''))
    tar.close()

    #From extracted config file get the name of database directory
    config = SafeConfigParser()
    config.read(os.path.join(destiantion, '') + "config")
    db_name = path_leaf(config.get('DB', 'db_path'))
    logger.debug('DB name extracted from config: ' + db_name)

    #Now we can read database
    database = leveldb.LevelDB(os.path.join(destiantion, '') + db_name)
    for key, value in database.RangeIter():
        (_, _, dropbox_file) = value.split(FileProcessor.HASH_SEPARATOR)

        #If dropbox file does not exist skip it
        dropbox_file_with_path = os.path.join(dropbox_path, '') + dropbox_file
        if not os.path.isfile(dropbox_file_with_path):
            logger.warning('File ' + dropbox_file_with_path +
                ' does not exist. Skipping.')
            continue

        #If destination file exists skip it
        if os.path.isfile(key):
            logger.info(key + ' already exists. Skiping.')
            continue

        logger.info('Extracting ' + key)

        dest_dir = ntpath.dirname(key)

        #Append topmost directory
        if override:
            override = os.path.join(override, '')
            dest_dir = '/' + override + dest_dir
            logging.debug('Overridden path: ' + dest_dir)

        dest_file_name = path_leaf(key)
        logger.debug('Dir: ' + dest_dir + ', file name: ' + dest_file_name)

        #Create destination directory if not present
        if not os.path.exists(dest_dir):
            logger.info(dest_dir + ' does not exitst. Creating.')
            os.makedirs(dest_dir)

        #Decrypt file
        decrypt_file(password, dropbox_file_with_path,
            os.path.join(dest_dir, '') + dest_file_name)
