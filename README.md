# Scavenger_Hunt
This is my NVIDIA project. It is an application that runs a flask app on the local network that allows multiple people to play a scavenger hunt game on multiple devices. The objective is to find whatever object the game tells you to find, and the game will know if you found it using an object detection model.

---------------------AI MODEL---------------------

The model was trained using the jetson-inference detectnet.

The dataset I used can be found at https://universe.roboflow.com/customdatasetyolov8/objects-common-in-ccs

I trained the model with 200 epochs and the default learning rate and batch size.

---------------------GAMEPLAY---------------------

Youtube video: https://youtu.be/fUuX2dF2iHM

If the youtube video doesn't work, you can download the video here: https://drive.google.com/file/d/1FWbshRrPS0YmSFdE0afjmftXEk1BP6cj/view?usp=sharing

If that doesn't work just read below

If that doesn't work I don't know what to tell you

Joining a Game

The game can be played alone or with friends.
On the home page, players enter their name and choose an avatar.
Players can either:
Create a room, which generates a game PIN.
Join a room using another player's game PIN.
The host sees the host controls, while other players see a waiting screen.
Setting Up the Game

The host chooses:

Round duration
Number of rounds
Item pool

Once everything is configured, the host can start the game.

Playing a Round

Players receive a prompt telling them which object to find.
Players have the amount of time set by the host to put the object in front of their camera.
The object detection model checks whether the correct object is visible.
When detected, a progress circle begins filling toward 100%.
The object must remain visible for 1–2 seconds before the find is confirmed. This prevents brief detection errors from counting as a successful find.

Scoring & Leaderboard

When a player finds the object, all players are notified of who found it and how many points they earned.
Other players can continue searching until the timer ends.
Points are awarded based on how quickly the object was found.
Players who fail to find the object receive 0 points.
After each round, a leaderboard displays all players and their scores.
The game only continues when the host presses Continue.

Leaving & Network Requirements

Players can leave at any time.
The host can end the game at any time.
Multiplayer requires everyone to be connected to the same network as the host server.
Using the host's mobile hotspot is recommended, since all players must be on the same network as the server.

<img width="2559" height="1414" alt="image" src="https://github.com/user-attachments/assets/4cdec3d9-d257-4315-9c08-95040d61e477" />


---------------------INSTALLATION INSTRUCTIONS---------------------

These are installations instructions for people who have a Windows desktop or laptop and uses Windows terminology and applications. Mac and Linux users will have to find their respective terms and applications, and try their best to follow along.

Hardware needed: Jetson Orin Nano, Desktop/Laptop with an internet connection and mobile hotspot capabilities
Software needed: Visual Studio Code, Web browser

1. Connect to your Jetson through VS Code using SSH (Make sure the Jetson is connected to your Desktop/Laptop's mobile hotspot)
2. In the "Explorer" section, create a folder for the application on your Jetson (ex. scavenger_app)

<img width="435" height="147" alt="Screenshot 2026-08-12 164426" src="https://github.com/user-attachments/assets/972c9e47-ed26-408d-87ed-cf69dc5b902b" />

3. Inside this folder, create two folders named "code" and "models" (case-sensitive)
4. Inside the "code" folder, make another folder named "templates"
5. Download app-v3.py, requirements.txt, and Dockerfile on your desktop/laptop and drag them into the "code" folder in the VS Code explorer (Dockerfile should have no extension)
6. Download index-v3.html into the "templates" folder in the VS Code explorer
7. Go to https://drive.google.com/file/d/1jLnXaLSxdoj2X8-nGSwbxKfQ4yKzVwEh/view?usp=sharing and download the .onnx file
8. Drag this .onnx file into the "models" folder in the VS Code explorer
9. Download labels.txt and put it into the "models" folder
10. You should now have app-v3.py, requirements.txt, and Dockerfile inside the "code" folder, index-v3.html inside the "templates" folder, and the .onnx file and labels.txt inside the "models" folder

<img width="369" height="430" alt="Screenshot 2026-08-12 164326" src="https://github.com/user-attachments/assets/499d263a-336e-45e3-a613-62ae4be25d73" />

NOTE: These files should be on your Jetson. We are just using VS Code to see what files are on your Jetson

11. Make sure you have python installed. If not, run "sudo apt update" then "sudo apt install python3 python3-pip python3-venv" in the terminal
12. Use "python3 --version" and "pip3 --version" to make sure everything is working
13. In the Jetson terminal in VS Code, use "cd" to move into the "code" folder (ex. "cd scavenger_app/code")
14. Run this command in the Jetson terminal in VS Code: "sudo docker build -t my-jetson-app ." (Yes, the period at the end is included.)
15. Run this command: "sudo docker run -it --runtime nvidia --network host -v $(pwd)/..:/app my-jetson-app"
16. When the docker container opens, enter "cd code"
17. Enter "python3 app-v3.py"
18. You should see lots of stuff come up in the terminal, but at the end you should see "Running on all addresses (0.0.0.0)", "Running on https://127.0.0.1:5000", "Running on https://(your jetson's ip address)", and "Press CTRL+C to quit"
19. To play the game, go into your web browser and type in "https://jetson-ip:5000" (replace jetson-ip with your jetson's ip address)

20. If you don't know how to find your jetson's ip address, follow these steps:
21. Open settings
22. Click Network & internet
23. Click Mobile hotspot
24. Your Jetson should be connected to your hotspot. If it is, look at the bottom of the "Properties" Section and you should see the devices connected and their names
25. Your Jetson's name should be something like nvidia-desktop if you didn't change it
26. The IP address of the jetson should be next to its name

<img width="2559" height="1533" alt="Screenshot 2026-08-12 163700" src="https://github.com/user-attachments/assets/9ffb4c3b-ded8-4d61-a83c-e2760f37c06e" />
