BINDIR		= ../sbin
SUSSH		= $(BINDIR)/sussh
SUSSH_OBJS	= sussh.o

COMMANDS	= $(SUSSH)
OBJS		= $(SUSSH_OBJS)

all: commands

commands: $(COMMANDS)

.o.c:
	$(CC) $(CFLAGS) -c $<


$(SUSSH): $(SUSSH_OBJS)
	$(CC) $(LFLAGS) -o $@ $<
