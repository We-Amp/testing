"""
Basic event handlers
"""

# :TODO(Piyush): rename this to event.py


class EventProcessor:
    """
    Class which want to register for events or post events needs to derive from this class.
    """

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

    def register_event(self, waitfor_event_name, wait_event, name, data):
        """
        Subclass should call this function when it wants to register custom event.
        It can be used to handle internal events without explicitly adding them to the test json
        """
        self.context.register_event(waitfor_event_name, wait_event, name, data)
