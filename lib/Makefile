all: libbkit

libbkit: builtins.o
	$(CC) -shared $(LDFLAGS) $< -o libbkit.so

install:
	mkdir -p $(PREFIX)/lib
	cp libbkit.so $(PREFIX)/lib/

clean:
	rm -f builtins.o libbkit.so
