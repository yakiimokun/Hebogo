BIN       = hebogo
TESTBIN   = hebogotest
MOD       = TAP
MODSRC    = test/tap.swift
COMMONSRC = \
			src/Board.swift src/Player.swift  src/Math.swift  src/UCTNode.swift  src/ReturnCode.swift \
			src/Stone.swift src/UCTPlayer.swift src/GTP.swift  src/PrimitiveMonteCarloPlayer.swift
BINSRC    = src/main.swift $(COMMONSRC)
TESTSRC   = $(MODSRC) test/main.swift $(COMMONSRC)
MODULE    = $(MOD).swiftmodule $(MOD).swiftdoc
SWIFTC    = swiftc -g
SWIFT     = swift

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
