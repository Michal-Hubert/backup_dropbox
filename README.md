# Background
As I am a little bit paranoic about backups I have decided to create a tool to help me with it and learn some python.
There are many tools for making backup so why yet another ? The reson is simple: at the moment I was writing
this tool there was no such. So what's special about it ? Before I answer to this question I will write my requirements about such tool: 
- Each backed up file shall be encrypted using AES
- The file name shall be changed so that even if someone has an access to storage the file name says nothing
- Support for incremental backup - only the files that changed are backed up
- Support for recovery 

The use case I had in mind is when we store backup on some remote storage like for example Dropbox. With this tool files are encrypted and have random names. You can achieve the same result if you create locally encrypted folder/disk and then upload it to Dropbox but with this approach any single file change causes the whole folder/disk to be uploaded again to Dropbox.
With this tool it's much simpler: just set as a destination of backup the local folder that is kept in sync with Dropbox and run the tool.
#How it works
First you need to create config file which looks like:

```
[Credentials]
password=jdndmnn$23

[DropBox]
drop_box_dir = /home/michal/backup

[DB]
#Database MUST not be in backed up folder as it's being changed
#during backup process. Program backs up databse itself by
#gzipping, encryptying and putting in drobox folder as "dbmapping"
db_path = /home/michal/db

[Backup]
to_backup = /media/sf_oem/Desktop/z
to_exclude =
```
So what we have here ? The _password_ is used for file encryption (during backup) and decryption (during recovery). Variable _drop_box_dir_ points to the directory being synced with Dropbox (or just any directory in which you want to store backup). The next _db_path_ is a directory where databse is created. What database ? In database I need to store checkums of files to determine if subsequent backup run shall backup file as it was changed or not. Moreover I store path of each backed up file as in Dropbox dir I don't create any subdirectories - all files are put in one dir. The next thing kept in database is file name (random string) assigned to file in Dropbox dir. 


Small example shall clarify it. Let's have the following tree to backup:

```
/home/michal/foo/bar/file1
/home/michal/foo/bar/cat/file2
```

After backup these two files are put in _drop_box_dir_ having some random names, for example _OSNRBZ_ and _PQQNJNY_. In database there are entries matching _/home/michal/foo/bar/file1_ to _OSNRBZ_ and _/home/michal/foo/bar/cat/file2_ to _PQQNJNY_.

#Usage 

###Back up
Create directory for databse then create config file with proper paths set up and then run: `python ds.py backup -c` 

