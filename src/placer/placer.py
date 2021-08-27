from abc import ABC, abstractmethod

class Placer(ABC):

    @abstractmethod
    def __init__(self, token_stream):
        pass

    @abstractmethod
    def place(self):
        """
        Takes in a TokenStream object and begins to place things down on
            token_stream.curr_document() based on the next Token in the TokenStream.
        """

