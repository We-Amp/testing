"""
Class which want to register for events or post events needs to derive from this class.
"""


class EventProcessor:
    def __init__(self, context):
        self.context = context

    def event_received(self, event_name, response, compare_func, event):
        """
        Subclass should call this function when it receives an event for which test can wait for
        response, a object on which future calls will be called.
        compare_func, a function object which will be called to
                     compare the data from test with received data in event.
                     compare_func should take two params, event which was received, data mentioned
                     in test.
        """
        self.context.event_received(event_name, response, compare_func, event)
