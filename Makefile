ANTLR_BUILD = bkit/parser/BKITParser.py

all: gen

gen: ${ANTLR_BUILD}

${ANTLR_BUILD}: grammar/BKIT.g4
	antlr -no-listener -visitor -Xexact-output-dir -o bkit/parser/ $<
	rm -f bkit/parser/*.interp bkit/parser/*.tokens

clean:
	rm -f bkit/parser/BKIT*.py

test_lexer: ${ANTLR_BUILD}
	@python -m unittest test.test_lexer

test_parser: ${ANTLR_BUILD}
	@python -m unittest test.test_parser

test_astgen: ${ANTLR_BUILD}
	@python -m unittest -f test.test_astgen

test_check:
	@python -m unittest -f test.test_check

test_codegen:
	@python -m unittest -f test.test_codegen

java/BKIT.g4: bkit/parser/BKIT.g4
	[ -d java ] || mkdir java
	sed -E ' /@lexer/,/^}/ d; /^options/ d; /self\.test/ d; s/\bboolean\b/bool/g' $< >$@

dist_ass1:
	@[ -d dist ] || mkdir dist
	sed 's/\.\.lexererr/lexererr/' bkit/parser/BKIT.g4 >dist/BKIT.g4
	./script/lexer_suite test/test_lexer.py >dist/LexerSuite.py
	./script/parser_suite test/test_parser.py >dist/ParserSuite.py
	./script/test_phung

dist_ass2:
	@[ -d dist ] || mkdir dist
	sed 's/\.\.lexererr/lexererr/' bkit/parser/BKIT.g4 >dist/BKIT.g4
	sed -e 's/^from \.parser/from BKITVisitor/' \
		-e 's/^from \.utils\.ast/from AST/' \
		bkit/astgen.py >dist/ASTGeneration.py
	./script/astgen_suite test/test_astgen.py >dist/ASTGenSuite.py
	# ./script/test_phung

dist_ass3:
	@[ -d dist ] || mkdir dist
	sed -e 's/^from \.\.utils\.ast/from AST/' \
		-e 's/^from \.\.utils\.visitor/from Visitor/' \
		-e 's/^from \.exceptions/from StaticError/' \
		bkit/checker/static_check.py >dist/StaticCheck.py
	./script/check_suite test/test_check.py >dist/CheckSuite.py
	./script/test_phung

dist_ass4: dist_ass2
	@[ -d dist ] || mkdir dist
	sed -e 's/^from \.\.utils\.ast/from AST/' \
		-e 's/^from \.\.utils\.visitor/from Visitor/' \
		-e 's/^from \.emitter/from Emitter/' \
		-e 's/^from \.frame/from Frame/' \
		-e 's/^from \. import emitter$$/import Emitter as emitter/' \
		bkit/codegen/code_generator.py >dist/CodeGenerator.py
	cp bkit/utils/type.py dist/Emitter.py
	printf '\n\n' >>dist/Emitter.py
	sed -e '/^from \.\.utils\.type/ d' \
		-e 's/^from \.exceptions/from CodeGenError/' \
		-e 's/^from \.machine_code/from MachineCode/' \
		-e 's/^from \.frame/from Frame/' \
		bkit/codegen/emitter.py >>dist/Emitter.py

	./script/codegen_suite test/test_codegen.py >dist/CodeGenSuite.py
	./script/test_phung4

.PHONY: all clean dist gen
