'''
Check consitency of database
'''

import logging
import leveldb
import os
import backup
from myutils import compute_hash, path_leaf
from file_processor import FileProcessor

def consistency_check(config, database):
    """
    DB->dropbox
    Consistency is when the db values (encrypted hash and encrypted file name )
    matches the dropbox file hash and name.

    dropbox->DB
    If there is no entry in db for fropbox file then it's incosistency and must
    be reported. It cannot be fixes automatically.

    I don't remove any file from dropbox. In some cases I just report problem
    which has to be manually fixed.
    """


    logger = logging.getLogger("mylog")
    dropbox_folder = config.get('DropBox', 'drop_box_dir')
    batch = leveldb.WriteBatch()

    #DB->dropbox
    #Little bit more verbose to report cases.

    dropbox_names = set()
    result = True

    for key, value in database.RangeIter():

        (_, encrypted_hash, dropbox_file) = \
            value.split(FileProcessor.HASH_SEPARATOR)
        dropbox_names.add(dropbox_file)
        dropbox_file = dropbox_folder + dropbox_file

        if not os.path.isfile(key):
            result = False
            batch.Delete(key)
            if not os.path.isfile(dropbox_file):
                logger.warning('File ' + dropbox_file + ' orginally ' + key +
                'does not exist in dropbox dir. Removing entry from db')
            else:
                #Only for informational purposes
                hsh = compute_hash(dropbox_file)
                if hsh != encrypted_hash:
                    logger.warning('File ' + dropbox_file + ' orginally ' +
                    key + 'has hash that does not match db entry. ' +
                    'Removing entry from db and file from dropbox')
        else:
            if not os.path.isfile(dropbox_file):
                result = False
                logger.warning('File ' + dropbox_file + ' orginally ' + key +
                    'does not exist in dropbox dir. Removing entry from db')
                batch.Delete(key)
            else:
                #Only for informational purposes
                hsh = compute_hash(dropbox_file)
                if hsh != encrypted_hash:
                    result = False
                    logger.warning('File ' + dropbox_file + ' orginally ' +
                    key + 'has hash that does not match db entry. ' +
                    'Removing entry from db')
                    batch.Delete(key)

    database.Write(batch, sync=True)

    #dropbox->DB
    for _, _, files in os.walk(dropbox_folder):
        for single_file in files:
            #Meta entry is not in database
            if path_leaf(single_file) == backup.META_DB_NAME + ".xyz":
                continue
            if single_file not in dropbox_names:
                result = False
                logger.warning('File ' + single_file +
                ' from dropbox does not have db entry !')

    return result
