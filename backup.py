"""
Process directories to be backed up
"""
import logging
import os
import leveldb
import tarfile
import tempfile
import shutil
import sys

from ConfigParser import SafeConfigParser
from file_processor import FileProcessor
from myutils import encrypt_file, path_leaf, query_yes_no, compute_hash
from consistency_check import consistency_check

#In this file database + config file are backed up
META_DB_NAME = "db_meta.tar"

def clean_removed(config, database):
    """
    Check if any file from source dir was removed.
    """

    logger = logging.getLogger('mylog')
    dropbox_folder = config.get('DropBox', 'drop_box_dir')
    batch = leveldb.WriteBatch()

    for key, value in database.RangeIter():

        #unencrypted_hash, encrypted_hash, dropbox_file
        (_, encrypted_hash, dropbox_file) = \
            value.split(FileProcessor.HASH_SEPARATOR)

        dropbox_file = os.path.join(dropbox_folder,'') + dropbox_file

        if not os.path.isfile(key):
            batch.Delete(key)
            if not os.path.isfile(dropbox_file):
                logger.warning('File ' + dropbox_file + ' originally ' + key + \
                    ' does not exist in dropbox dir. ' +
                    'Consistency check will catch it.')
            else:
                #Only for informational purposes
                hsh = compute_hash(dropbox_file)
                if hsh != encrypted_hash:
                    logger.warning('File ' + dropbox_file + ' originally ' +
                    key + ' has hash that does not match db entry.' +
                    'Consistency check will catch it.')
                else:
                    logger.info('File ' + dropbox_file + ' orginally ' + key + \
                        ' was removed. Removing backed up file...')
                    batch.Delete(key)
                    os.remove(dropbox_file)

    database.Write(batch, sync=True)

def backup(config, database):
    """
    Process directoreis to be backed up
    """
    logger = logging.getLogger('mylog')

    clean_removed(config, database)

    if not consistency_check(config, database):
        logger.warning('Consistency check detected problems!')
        if not query_yes_no('Continue?'):
            sys.exit()

    dirs = config.get('Backup', 'to_backup').split()
    logger.info('Directories to backup: ' + ','.join(dirs))

    exclude_dirs = config.get('Backup', 'to_exclude').split()
    logger.info('Directories to exclude: ' + ','.join(exclude_dirs))


    file_proc = FileProcessor(config, database, encrypt_file)

    #Count files to show progress later
    total = 0

    for directory in dirs:
        for subdir, _, files in os.walk(directory):
            if  subdir in exclude_dirs:
                continue

            for single_file in files:
                fpath = os.path.join(subdir, single_file)
                total = total + 1

    count = 0
    for directory in dirs:
        logger.debug('Processing directory' + directory)
        for subdir, dirs, files in os.walk(directory):
            if  subdir in exclude_dirs:
                logger.debug('Skipping directory' + subdir)
                continue

            for single_file in files:
                fpath = os.path.join(subdir, single_file)
                logger.debug('Processing file ' + fpath)
                logger.info(str((count * 100) / total) + ' %')
                file_proc.process(fpath)
                count = count + 1

def backup_meta(config_path):
    '''
    Makes tar out of database directory + config, encrypts it and copies
    to dropbox folder as 'meta' file
    '''
    logger = logging.getLogger('mylog')

    config = SafeConfigParser()
    config.read(config_path)
    db_path = config.get('DB', 'db_path')
    password = config.get('Credentials', 'password')
    logger.info('Backing up database ' + db_path)

    temp_dir = tempfile.gettempdir()
    archive = temp_dir + '/' + META_DB_NAME
    with tarfile.open(archive, "w:") as tar:
        tar.add(db_path, arcname=path_leaf(db_path))
        tar.add(config_path, arcname=path_leaf(config_path))
        tar.close()
        enc_file_name = encrypt_file(password, archive)
        #Remove unencrypted file
        os.remove(archive)
        #Move encrypted meta file to dropboxdir
        dropboxdir = config.get('DropBox', 'drop_box_dir')

        if os.path.isfile(os.path.join(dropboxdir, '') +
        path_leaf(enc_file_name)):
            os.remove(os.path.join(dropboxdir, '') + path_leaf(enc_file_name))
        shutil.move(enc_file_name, dropboxdir)
        logger.info('Database was backed up.')

def dump_database(database, out_file):
    '''
    Dump content of database
    '''
    entires = 0
    with open(out_file, 'w') as output:
        output.write('<HTML>')
        output.write('<HEAD></HEAD>')
        output.write('<BODY>')
        output.write('<TABLE border="1" style="width:100%">')
        output.write('<TR><TH>Backed up file</TH>'+
            '<TH>Unecrypted hash</TH><TH>Encrypted hash</TH>'+
            '<TH>Dropbox file</TH></TR>')
        for key, value in database.RangeIter():
            (unencrypted_hash, encrypted_hash, dropbox_file) = \
                value.split(FileProcessor.HASH_SEPARATOR)
            #print key + ' -> unencrypted hash: ' + unencrypted_hash + \
            #' encrypted hash ' + encrypted_hash +  ' dropbox file ' +  dropbox_file
            #print '-'*80
            output.write('<TR><TD>' + key + '</TD><TD>' + unencrypted_hash + \
                '</TD><TD>' + encrypted_hash + '</TD><TD>' + dropbox_file +
                '</TD></TR>')
            entires = entires + 1
        output.write('</TABLE>')
        output.write('</BODY>')
        output.write('</HTML>')
    return entires

