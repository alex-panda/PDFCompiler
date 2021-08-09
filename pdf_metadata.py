from tools import assert_subclass, assert_instance


class PDFMetadata:
    """
    A class meant for setting and getting the general settings of the PDF. For
    example, the PDF can be given an Author and Description, so you would set
    it on this object and then it will be on the PDF later.
    """
    def __init__(self):
        self._title = None
        self._subject = None
        self._author = None
        self._creator = None
        self._keywords = None

    def title(self):
        return self._title

    def set_title(self, new_title):
        assert_instance(new_title, str, 'title')
        self._title = new_title

    def apply_to_canvas(self, canvas_obj):
        """
        Applies this PDFMetadata to the given Canvas.
        """
        c = canvas_obj

        if self._title:
            c.setTitle(self._title)

        if self._subject:
            c.setSubject(self._subject)

        if self._author:
            c.setAuthor(self._author)

        if self._creator:
            c.setCreator(self._creator)

        if self._keywords:
            c.setCreator(self._keywords)
