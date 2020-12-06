ANTLR_CMD = java org.antlr.v4.Tool -no-listener -visitor -Xexact-output-dir
ANTLR_BUILD = bkit/parser/antlr_build/BKITParser.py

all: gen

gen: ${ANTLR_BUILD}

${ANTLR_BUILD}: bkit/parser/BKIT.g4
	${ANTLR_CMD} -o bkit/parser/antlr_build/ $<

clean:
	rm -f bkit/parser/antlr_build/BKIT*

test_lexer: ${ANTLR_BUILD}
	@python -m unittest test.test_lexer

test_parser: ${ANTLR_BUILD}
	@python -m unittest test.test_parser

java/BKIT.g4: bkit/parser/BKIT.g4
	[ -d java ] || mkdir java
	sed -E ' /@lexer/,/^}/ d; /^options/ d; /self\.test/ d; s/\bboolean\b/bool/g' $< >$@

dist_ass1:
	@[ -d dist ] || mkdir dist
	sed 's/\.\.lexererr/lexererr/' bkit/parser/BKIT.g4 >dist/BKIT.g4
	./script/lexer_suite test/test_lexer.py >dist/LexerSuite.py
	./script/parser_suite test/test_parser.py >dist/ParserSuite.py
	./script/test_phung

.PHONY: all clean dist gen
