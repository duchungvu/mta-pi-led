# Hardware

These are the hardware that I use to show the info:

- LED Panel: 64x32 P4 single panel
- Raspberry Pi: Model 3 with RGB Matrix Bonnet/HAT
- Connection: HUB75 interface via Adafruit RGB Matrix Bonnet

# Development patterns

- We're working on a local version of the code on this environment, on a different terminal, I will call rsync to sync it with the RPI. If you're running command or code, always assume that you're on the local dev not the Pi.
- We have a FEATURES.md file that will keep track of the DONE/IN PROGRESS/TO DO features we want to build. Update they if we decide to take on a new task or add more if there are features I want to add
- For long or complex tasks, write TODO or keep track of the task in the `/features` folder. Each feature should have one file that describes clearly what we're building, TODO and the progrss so far so that we can reference it in the future

# Code styles

- Avoid hard-coded values
- Always write reusable code
- Always organize the code in the right directory
- Delete temporary files if necessary

# Other instructions

- Don't read `.cursorrules` if you're not on Cursor