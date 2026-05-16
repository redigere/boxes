from __future__ import annotations

import struct

from boxes.services.spice.spice_channel import SPICEChannel


class SPICEInput:
    """SPICE input channel for keyboard and mouse forwarding.

    Sends keyboard scancodes and mouse motion/button events to the
    SPICE guest agent.
    """

    SPICE_MSGC_INPUT_KEY_DOWN = 101
    SPICE_MSGC_INPUT_KEY_UP = 102
    SPICE_MSGC_INPUT_MOUSE_MOTION = 111
    SPICE_MSGC_INPUT_MOUSE_BUTTON = 112

    def __init__(self, channel: SPICEChannel) -> None:
        self._channel = channel
        self._mouse_x: int = 0
        self._mouse_y: int = 0
        self._buttons: int = 0

    @property
    def mouse_x(self) -> int:
        return self._mouse_x

    @property
    def mouse_y(self) -> int:
        return self._mouse_y

    def send_key_down(self, scancode: int) -> None:
        """Send a key press event."""
        if not self._channel.connected:
            return
        data = struct.pack("!IB", self.SPICE_MSGC_INPUT_KEY_DOWN, scancode)
        try:
            self._channel.send(data)
        except ConnectionError:
            pass

    def send_key_up(self, scancode: int) -> None:
        """Send a key release event."""
        if not self._channel.connected:
            return
        data = struct.pack("!IB", self.SPICE_MSGC_INPUT_KEY_UP, scancode)
        try:
            self._channel.send(data)
        except ConnectionError:
            pass

    def send_mouse_motion(self, x: int, y: int) -> None:
        """Send a mouse move event to the guest."""
        if not self._channel.connected:
            return
        self._mouse_x = x
        self._mouse_y = y
        data = struct.pack("!Iii", self.SPICE_MSGC_INPUT_MOUSE_MOTION, x, y)
        try:
            self._channel.send(data)
        except ConnectionError:
            pass

    def send_mouse_button(self, button: int, pressed: bool) -> None:
        """Send a mouse button event (1=left, 2=middle, 3=right)."""
        if not self._channel.connected:
            return
        if pressed:
            self._buttons |= (1 << (button - 1))
        else:
            self._buttons &= ~(1 << (button - 1))
        data = struct.pack("!III", self.SPICE_MSGC_INPUT_MOUSE_BUTTON, button, int(pressed))
        try:
            self._channel.send(data)
        except ConnectionError:
            pass

    def reset(self) -> None:
        """Reset all input state."""
        self._mouse_x = 0
        self._mouse_y = 0
        self._buttons = 0
