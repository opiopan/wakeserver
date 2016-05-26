#include <stdlib.h>
#include <stdio.h>
#include <sys/types.h>
#include <unistd.h>
#include <pwd.h>

static void errorexit()
{
    perror("sussh");
    exit(1);
}

int main(int argc, char** argv)
{
    const char* user;
    const char* host;
    const char* command;
    struct passwd* entry;

    if (argc < 4){
	fprintf(stderr, "usage: sussh user host command\n");
	exit(1);
    }

    user = argv[1];
    host = argv[2];
    command = argv[3];

    if (!(entry = getpwnam(user))){
	errorexit();
    }

    setenv("HOME", entry->pw_dir, 1);

    if (setuid(entry->pw_uid) != 0 || seteuid(entry->pw_uid) != 0){
	errorexit();
    }

    execl("/usr/bin/ssh", "ssh", host, command, NULL);

    errorexit();

    return -1;
}

