### Warning: Much of what is written below is just planned and not yet implemented.

# PDFCompiler

A compiler that creates richtext PDFs (the PDF's text is bolded, italicized,
    underlined, etc.) from plain text files such as .txt files. Enriching
    the document's text can be done either through Command Sequences,
    which are a excedingly simple to use, or through the use of the programming
    language Python which can be embeded directly into your document (i.e. you
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
python code so there is nothing that you can do with commands that you cannot
do with Python, commands are just far more convenient.

For a more in-depth look at commands, look at the command section of the
    tutorial.

## Python Integration

The first thing you need to know is that the Compiler passes over your
plaintext document twice, allowing you to run Python code on either pass 1 or
pass 2. Pass one is when all the commands of the document are run and a "token
document" (which is just a list of all the tokens that make up your document)
is created. This token document is then given to a Placer object which just
reads the token document token by token (so word by word, affectively) and puts
each one on your PDF.

Note: Even though there are two different passes, variables assigned in the
first pass do carry over to the second pass. For example, if you assign "x
= 0" in pass 1 Python code, then you will be able to access x in pass 2
Python code. Of course, the opposite is not true because pass 2 Python code
is run after pass 1 Python code so if you assign "x = 0" in pass 2 Python
code you cannot get the value of x in pass 1 because "x = 0" has not been
run yet.

When designating Python code, you can either designate one line of it or
multiple lines. The single-line syntax is

\>print('This is Python code because of the \\>')

and the multi-line syntax is

\->
print('This is Python code because of the \\-><-\\')
<-\

with everything in-between the arrows being Python code. Of course, all
white space between the arrows is included so be careful that the code is
properly indented or else Python will raise an error.

By default, the designated code will be run in the first pass. If you want
to designate code to be run on the second pass, then you must do

\2>

or

\2-><-\

and the 2 will designate it as Python code to be run on the second pass.

For a more in-depth look at how to use python, look at the python section of
the tutorial.


