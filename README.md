# Warning: Much of what is written below is just planned and not yet implemented.


# PDFCompiler

NOTE: You do not need to use any Python if you want to use this Compiler.
    You can peek at the Command Sequences section if you want to see the
    super-easy commands you can use to change your text without any
    Python whatsoever.

This is a program that takes a plain-text input file and compiles it into a
    custom PDF using Python. In fact, Python can be embeded in the file
    (written directly in designated areas of the file) and can directly
    change what the PDF will look like in the end.

## Getting Started

You actually do not need to put any Python in your files if you do not
    want to. Just write some text in a file like so:

    Hello. Testing, 1, 2, 3.

    and then compile it using python compile.py ./path/to/your/file.pdfo

    Then it will be compiled and you should get a nice output PDF with the
    text being laid out in a paragraph format. But you probably want more than
    that, in which case you just need to know about commands and what they can
    do.

## Command Sequences

If you are coming from latex, these should be familiar to you. They allow
    you to conveniently specify text to run code on and "command" the given
    text be a certain way. These include, but are not limited to:

    \bold{text to bold}
    \it{text to italisize}
    \underline{text to underline}
    \font{name of font to change to}{text to change to specified font}

    These are what most people will use most of the time because of how
    convenient they are to use, but do realize that most of them are just
    wrappers for python code so if you want to do something Hyper-Complex
    or that noone has written a package for yet, you will probably need
    to know a bit of Python, but 99% of what most people will want to do
    can be done through Command Sequences alone.

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

The fact that there is 
