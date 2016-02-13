BIN     = hebogo
TESTBIN = hebogotest
MOD     = TAP
MODSRC  = test/tap.swift
BINSRC  = src/main.swift src/Board.swift
TESTSRC = $(MODSRC) test/main.swift src/Board.swift
MODULE  = $(MOD).swiftmodule $(MOD).swiftdoc
SWIFTC  = swiftc
SWIFT   = swift

ifdef SWIFTPATH
	SWIFTC=$(SWIFTPATH)/swiftc
	SWIFT=$(SWIFTPATH)/swift
endif

OS := $(shell uname)

ifeq ($(OS),Darwin)
	SWIFTC=xcrun -sdk macosx swiftc
endif

all: $(BIN)

module: $(MODULE)

clean:
	-rm $(BIN) $(MODULE) lib$(MOD).*

$(BIN): $(BINSRC)
	$(SWIFTC) -o $(BIN) $(BINSRC)

test: $(TESTBIN)
	prove ./$(TESTBIN)

$(TESTBIN): $(TESTSRC)
	$(SWIFTC) -o $(TESTBIN) $(TESTSRC)

$(MODULE): $(MODSRC)
	$(SWIFTC) -emit-library -emit-module $(MODSRC) -module-name $(MOD)

repl: $(MODULE)
	$(SWIFT) -I. -L. -l$(MOD)
