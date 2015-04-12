'''
End to end testing
'''
import shutil
import os
from ConfigParser import SafeConfigParser
import textwrap
import hashlib
import pexpect
import sys
import leveldb
import backup
from backup import debug_db_dump
from myutils import path_leaf

TEST_CONFIG_NAME = "config"
TEST_DROPBOX_NAME = "dropbox"
TEST_TO_BACKUP_DIR = "to_backup"
TEST_DATABASE_DIR = "db"
TEST_PATH = os.path.dirname(os.path.abspath(__file__)) + '/test/'
#Path wehre db will be recovered
DB_RECOVERY_PATH = os.path.dirname(os.path.abspath(__file__)) + '/foo/'
PASSWORD = "alamakota"

BACKUP_TOOL = "python ./ds.py "

def reset_dropbox_dir(config):
    '''
    Remove dropbox dropbox directory
    '''
    dropbox_dir = config.get('DropBox', 'drop_box_dir')
    shutil.rmtree(dropbox_dir)
    os.makedirs(dropbox_dir)

def reset_db(config):
    '''
    Remove databse
    '''
    db_dir = config.get('DB', 'db_path')
    shutil.rmtree(db_dir)
    os.makedirs(db_dir)

def reset_to_backup_dir(config):
    '''
    Remove directory to backed up
    '''
    to_backup_dir = config.get('Backup', 'to_backup')
    shutil.rmtree(to_backup_dir)
    os.makedirs(to_backup_dir)

def create_test_config():
    '''
    Creates config file for testing purposes
    '''
    aa = """\
    [Credentials]
    password=alamakota

    [DropBox]
    drop_box_dir = {drop_box_dir}

    [DB]
    #Database MUST not be in backed up folder as it's being changed
    #during backup process. Program backs up databse itself by
    #gzipping, encryptying and putting in drobox folder as "dbmapping"
    db_path = {db_path}

    [Backup]
    to_backup = {to_backup}
    to_exclude =
    """
    context = {
      "drop_box_dir":TEST_PATH+TEST_DROPBOX_NAME+"/",
      "db_path":TEST_PATH+TEST_DATABASE_DIR+"/",
      "to_backup":TEST_PATH+TEST_TO_BACKUP_DIR+"/",
      "passord":PASSWORD
    }

    if not os.path.exists(TEST_PATH):
        os.makedirs(TEST_PATH)

    with open(TEST_PATH+'/'+TEST_CONFIG_NAME, 'w') as cfgfile:
        cfgfile.write(textwrap.dedent(aa.format(**context)))

    if not os.path.exists(context["drop_box_dir"]):
        os.makedirs(context["drop_box_dir"])
    if not os.path.exists(context["db_path"]):
        os.makedirs(context["db_path"])
    if not os.path.exists(context["to_backup"]):
        os.makedirs(context["to_backup"])

    if not os.path.exists(DB_RECOVERY_PATH):
        os.makedirs(DB_RECOVERY_PATH)


def clear(config):
    '''
    Clears all created files, directories and exits
    '''
    db_dir = config.get('DB', 'db_path')
    if os.path.exists(db_dir):
        shutil.rmtree(db_dir)
    dropbox_dir = config.get('DropBox', 'drop_box_dir')
    if os.path.exists(dropbox_dir):
        shutil.rmtree(dropbox_dir)
    to_backup_dir = config.get('Backup', 'to_backup')
    if os.path.exists(to_backup_dir):
        shutil.rmtree(to_backup_dir)
    os.remove(TEST_PATH+TEST_CONFIG_NAME)

def clear_all():
    '''
    Remove all in one shot
    '''
    if os.path.exists(TEST_PATH):
        shutil.rmtree(TEST_PATH)

    if os.path.exists(DB_RECOVERY_PATH):
        shutil.rmtree(DB_RECOVERY_PATH)

def test1():
    '''
    Initially dropbox folder is empty and databse is empty.
    Check if file is backed up and restored correctly
    '''
    print '-'*50
    print "Test 1"
    clear_all()
    create_test_config()
    config = SafeConfigParser()
    config.read(TEST_PATH+TEST_CONFIG_NAME)
    file_to_backup = config.get('Backup', 'to_backup')+'/some_file'
    with open(file_to_backup, 'w') as some_file:
        some_file.write('Very first line')
    checksum_before = hashlib.md5(open(file_to_backup, 'rb').read()).hexdigest()

    #Backup
    os.system(BACKUP_TOOL + "backup -c" + TEST_PATH + "/" + TEST_CONFIG_NAME)

    #Restore
    os.remove(file_to_backup)
    child = pexpect.spawn(BACKUP_TOOL + "restore -d" + TEST_PATH+
      TEST_DROPBOX_NAME + " -r" + DB_RECOVERY_PATH)
    child.expect('Password: ')
    child.sendline(PASSWORD)
    print child.read()

    checksum_after = hashlib.md5(open(file_to_backup, 'rb').read()).hexdigest()
    if checksum_before != checksum_after:
        print "Test 1 failed!"
        sys.exit(1)
    else:
        print "Test 1 ok"

def test2():
    '''
    Initally dropbox folder is empty and database is empty.
    Check if modified file is backed up and restored correctly.
    '''
    print '-'*50
    print "Test 2"
    clear_all()
    create_test_config()
    config = SafeConfigParser()
    config.read(TEST_PATH+TEST_CONFIG_NAME)
    file_to_backup = config.get('Backup', 'to_backup')+'/some_file'
    with open(file_to_backup, 'w') as some_file:
        some_file.write('Very first line')

    #Backup
    os.system(BACKUP_TOOL + "backup -c" + TEST_PATH + "/" + TEST_CONFIG_NAME)

    #Modification
    with open(file_to_backup, 'a') as some_file:
        some_file.write('The second line')
    checksum_before = hashlib.md5(open(file_to_backup, 'rb').read()).hexdigest()

    #Backup
    os.system(BACKUP_TOOL + "backup -c" + TEST_PATH + "/" + TEST_CONFIG_NAME)

    #Restore
    os.remove(file_to_backup)
    child = pexpect.spawn(BACKUP_TOOL + "restore -d " + TEST_PATH+
      TEST_DROPBOX_NAME + " -r " + DB_RECOVERY_PATH)
    child.expect('Password: ')
    child.sendline(PASSWORD)
    print child.read()

    checksum_after = hashlib.md5(open(file_to_backup, 'rb').read()).hexdigest()
    if checksum_before != checksum_after:
        print "Test 2 failed!"
        sys.exit(1)

    db = leveldb.LevelDB(config.get('DB', 'db_path'))
    entries = debug_db_dump(db)

    if entries != 1:
        print "Test 2 failed!"
        sys.exit(1)

    print "Test 2 ok"

def test3():
    '''
    Initally dropbox folder is empty and database is empty.
    Check if deleted files in source folder is deleted from dropbox as well
    '''
    print '-'*50
    print "Test 3"
    clear_all()
    create_test_config()
    config = SafeConfigParser()
    config.read(TEST_PATH+TEST_CONFIG_NAME)
    file_to_backup = config.get('Backup', 'to_backup')+'/some_file'
    with open(file_to_backup, 'w') as some_file:
        some_file.write('Very first line')

    #Backup
    os.system(BACKUP_TOOL + "backup -c" + TEST_PATH + "/" + TEST_CONFIG_NAME)

    #Delete
    os.remove(file_to_backup)

    #Backup again
    os.system(BACKUP_TOOL + "backup -c" + TEST_PATH + "/" + TEST_CONFIG_NAME)

    #Check if file doesn't exist
    for subdir, dirs, files in os.walk(config.get('DropBox','drop_box_dir')):
        for f in files:
            #Meta entry is not in database
            if path_leaf(f) == backup.META_DB_NAME + ".xyz":
                continue
            else:
                print "Test 3 failed - deleted file exists in dropbox folder"
                sys.exit(1)

    #Database shall not contain any entry
    entries = 0
    db = leveldb.LevelDB(config.get('DB', 'db_path'))
    entries = debug_db_dump(db)
    if entries != 0:
        print "Test 3 failed - deleted file has entry in database"
        sys.exit(1)

    print "Test 3 ok"

def test4():
    '''
    Initally dropbox folder is empty and database is empty.
    Check if deleted source folder (which contains files) causes deletion
    of this files from dropbox folder.
    '''
    print '-'*50
    print "Test 4"
    clear_all()
    create_test_config()
    config = SafeConfigParser()
    config.read(TEST_PATH+TEST_CONFIG_NAME)

    directory_to_backup = config.get('Backup', 'to_backup')+'/some_dir'
    os.makedirs(directory_to_backup)

    file_to_backup = config.get('Backup', 'to_backup')+'/some_dir/some_file1'
    with open(file_to_backup, 'w') as some_file:
        some_file.write('Very first line')

    file_to_backup = config.get('Backup', 'to_backup')+'/some_dir/some_file2'
    with open(file_to_backup, 'w') as some_file:
        some_file.write('The other very first line')

    #Backup
    os.system(BACKUP_TOOL + "backup -c" + TEST_PATH + "/" + TEST_CONFIG_NAME)

    #Delete
    shutil.rmtree(directory_to_backup)

    #Backup again
    os.system(BACKUP_TOOL + "backup -c" + TEST_PATH + "/" + TEST_CONFIG_NAME)

    #Check if file doesn't exist
    for subdir, dirs, files in os.walk(config.get('DropBox','drop_box_dir')):
        for f in files:
            #Meta entry is not in database
            if path_leaf(f) == backup.META_DB_NAME + ".xyz":
                continue
            else:
                print "Test 4 failed - deleted file exists in dropbox folder"
                sys.exit(1)

    #Database shall not contain any entry
    entries = 0
    db = leveldb.LevelDB(config.get('DB', 'db_path'))
    entries = debug_db_dump(db)
    if entries != 0:
        print "Test 4 failed - deleted file has entry in database"
        sys.exit(1)

    print "Test 4 ok"

def run_tests():
    '''
    Run test cases
    '''
    test1()
    test2()
    test3()
    test4()
    clear_all()

if __name__ == "__main__":
    #TEST_PATH = os.path.dirname(os.path.abspath(__file__)) + '/test/'
    run_tests()

