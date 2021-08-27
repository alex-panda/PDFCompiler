### Warning: Much of what is written below is just planned and not yet implemented.

# PDFCompiler

A compiler that creates richtext PDFs (the PDF's text is bolded, italicized,
    underlined, etc.) from plain text files such as .txt files. Enriching
    the document's text can be done either through Command Sequences,
    which are an excedingly simple to use, or through the use of the programming
    language Python which can be embeded directly in your documents (i.e. you
    can designate Python code directly in your plain text document and the
    compiler will run the code).

A short introduction to the compiler is provided below and a tutorial is
    provided in the tutorial folder.

## Command Sequences

If you are coming from LaTeX, these should be familiar to you. They allow
    you to conveniently "command" text be a certain way. You use a backslash
    "\" and then the name of a command to specify what command you want to
    use, and then you given the command "arguments" by putting the text you
    want to command inside curly bracktes "{}". A few examples would be:

    \b{text to bold}
    \i{text to italisize}
    \underline{text to underline}
    \font{name of font to change to}{size of font}{text to change to
        specified font and font size}

    As you can see, not all commands take just one argument. Some take
    additional arguments such as the name of a font and the size of the font.

    Some commands also store information that will be added to the meta-data
    of the PDF. A few examples include:

    \title{The Title of Your PDF}
    \author{The Author of Your PDF}
    \created{The Creation Date of the PDF}

    Other commands take no arguments at all. An example of this would be

    \available_fonts

    which searches the most common places for fonts to be on your computer and
    writes the names of the fonts it found on your PDF. This command in
    particular is meant to help you figure out what fonts you have available
    to use in your PDF.

Commands are what most people will use majority of the time because of how
    convenient they are, but do realize that most of them are just wrappers for
    python code so there is nothing that you can do with commands that you
    cannot do with Python, commands are just far more convenient.

## Python Integration

The first thing you need to know is that the Compiler passes over your
    plaintext document twice, allowing you to designate python code you want
    to run on either pass 1 or 2. Why is this the case? So that you can do things
    like index all your chapters on the first pass and then print out a nice
    table of their titles and page numbers before the rest of the document is
    printed out.

Another VERY important thing to know is that the first pass is just that, a
    first pass. None of your PDF is actually written on it. On the second one,
    however, the Compiler is actively writing your PDF when the code is run, so
    this is the pass you want to be doing things like changing your fonts and
    bolding your text because this is where it will actually be done.

