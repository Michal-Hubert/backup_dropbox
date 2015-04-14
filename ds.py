
#!/usr/bin/python
import logging
import sys
import os
import leveldb
import argparse

from ConfigParser import SafeConfigParser
from backup import backup, backup_meta
from restore import restore

def setup_logging():
    """
    Set up logging
    """
    level = logging.DEBUG
    root = logging.getLogger('mylog')
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s - %(filename)s:%(lineno)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)

def main():
    """
    Main routine
    """
    parser = argparse.ArgumentParser(description='Backup/Restore')

    subparsers = parser.add_subparsers()

    backup_parser = subparsers.add_parser('backup', help='do backup')
    backup_parser.add_argument('-c', nargs=1, required=True,
        metavar='config_file')


    restore_parser = subparsers.add_parser('restore', help='do restore')
    restore_parser.add_argument('-d', nargs=1, required=True,
        metavar='dropbox directory')
    restore_parser.add_argument('-r', nargs=1, required=True,
        metavar='directory for database restoral')
    restore_parser.add_argument('-o', nargs=1, metavar='override the root of ' +
        ' directories')

    args = parser.parse_args()

    setup_logging()

    try:
        if hasattr(args, 'c'):
            config_path = args.c[0]
            if not os.path.isfile(config_path):
                logging.error('Config file ' + config_path +' does not exist')
                return

            config = SafeConfigParser()
            config.read(config_path)
            database = leveldb.LevelDB(config.get('DB', 'db_path'))
            backup(config, database)
            backup_meta(config_path)
        else:
            override = ''
            if hasattr(args, 'o'):
                override = args.o[0]
            restore(args.d[0], args.r[0], override)
    except KeyError:
        print 'Key not found!'
    except SystemExit:
        print 'Exiting...'

if __name__ == '__main__':
    main()


