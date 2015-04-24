
#!/usr/bin/python
import logging
import sys
import os
import leveldb
import argparse

from collections import namedtuple

from ConfigParser import SafeConfigParser
from backup import backup, backup_meta, dump_database
from restore import restore
from consistency_check import consistency_check

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

def setup_config(config_path):
    '''
    Setup config parser and opens database
    '''
    if not os.path.isfile(config_path):
        logging.error('Config file ' + config_path +' does not exist')
        raise SystemExit

    config = SafeConfigParser()
    config.read(config_path)
    database = leveldb.LevelDB(config.get('DB', 'db_path'))

    ret = namedtuple('ret', 'config config_path database')
    return ret(config, config_path, database)


def main():
    """
    Main routine
    """
    parser = argparse.ArgumentParser(description='Backup/Restore')

    subparsers = parser.add_subparsers(dest='cmd')

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

    consitency_parser = subparsers.add_parser('consistency',
        help='do consistency')
    consitency_parser.add_argument('-c', nargs=1, required=True,
        metavar='config_file')

    dump_parser = subparsers.add_parser('dump', help='do dump')
    dump_parser.add_argument('-c', nargs=1, required=True,
        metavar='config_file')
    dump_parser.add_argument('-f', nargs=1, required=True,
        metavar='output_file')


    args = parser.parse_args()

    setup_logging()

    try:
        if args.cmd == 'backup':
            res = setup_config(args.c[0])
            backup(res.config, res.database)
            backup_meta(res.config_path)
        elif args.cmd == 'restore':
            override = ''
            if args.o:
                override = args.o[0]
            restore(args.d[0], args.r[0], override)
        elif args.cmd == 'consistency':
            logger = logging.getLogger('mylog')
            res = setup_config(args.c[0])
            res = consistency_check(res.config, res.database, True)
            if res is True:
                logger.info('Consistency check completed successfully')
            else:
                logger.info('Consistency check has found some problems.' +
                    ' Rerun to check if they were fixed.')
        elif args.cmd == 'dump':
            res = setup_config(args.c[0])
            dump_database(res.database, args.f[0])

    except KeyError:
        print 'Key not found!'
    except SystemExit:
        print 'Exiting...'

if __name__ == '__main__':
    main()


