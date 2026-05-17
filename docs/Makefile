PANDOC   = pandoc
MMDC     = ./node_modules/.bin/mmdc
PUPPETEER_CFG = puppeteer-config.json

.PHONY: pdf diagrams clean

pdf: diagrams relatorio.pdf

diagrams:
	$(MMDC) --puppeteerConfigFile $(PUPPETEER_CFG) -i diagrams/arquitetura.mmd    -o diagrams/arquitetura.png    -b transparent
	$(MMDC) --puppeteerConfigFile $(PUPPETEER_CFG) -i diagrams/seq-callback.mmd   -o diagrams/seq-callback.png   -b transparent
	$(MMDC) --puppeteerConfigFile $(PUPPETEER_CFG) -i diagrams/seq-game-event.mmd -o diagrams/seq-game-event.png -b transparent

relatorio.pdf: relatorio.md diagrams/arquitetura.png diagrams/seq-callback.png diagrams/seq-game-event.png
	$(PANDOC) relatorio.md \
	  -o relatorio.pdf \
	  --pdf-engine=xelatex \
	  -V geometry:margin=2cm \
	  -V fontsize=11pt \
	  -V lang=pt-BR \
	  --highlight-style=tango

clean:
	rm -f relatorio.pdf diagrams/*.png
