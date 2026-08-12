# Scavenger_Hunt
This is my NVIDIA project. It is an application that runs a flask app on the local network that allows multiple people to play a scavenger hunt game on multiple devices. The objective is to find whatever object the game tells you to find, and the game will know if you found it using an object detection model.

---------------------AI MODEL---------------------

The model was trained using the jetson-inference detectnet.

The dataset I used can be found at https://universe.roboflow.com/customdatasetyolov8/objects-common-in-ccs

I trained the model with 200 epochs and the default learning rate and batch size.

---------------------GAMEPLAY---------------------

This game can be played alone or with friends. When first opening the application, the user will see a home page with an option to enter a name and pick an avatar. After creating their player, they can either create a room or join another user's room via a game pin. Game pins are generated after a player creates a room. After joining a room, the user will either see host controls (if they started the room) or will see a waiting screen. After the host sets the round duration, number of rounds, and the item pool, they can start the game. During the game, the user will see a prompt to find an object. Depending on how long the host decided, the user has a certain amount of time to put the object in view of the camera. If the object detection model sees the correct object, it will start to fill up the progress circle up to 100%. Wins are not instantaneous, it requires the object to be held in view for a second or two. This prevents accidental detections where the model has a brief split second mistake. When someone finds the object, the app will let all user know who found the object and how many points they get. Other players will still have the chance to find the object until the timer runs out. Points are awarded based on speed. 0 points are awarded to players who failed to find the object. At the end of the round a leaderboard will show with all players and their points. During this time the game will only move on once the host clicks the continue button. All user's can leave at any time, and the host can end the game at any time. Unfortunately, in order to play the game with friends you must be on the same network. Connecting to the mobile hotspot of the host server is recommended.
<img width="2559" height="1414" alt="image" src="https://github.com/user-attachments/assets/4cdec3d9-d257-4315-9c08-95040d61e477" />


---------------------INSTALLATION INSTRUCTIONS---------------------

These are installations instructions for people who have a Windows desktop or laptop and uses Windows terminology and applications. Mac and Linux users will have to find their respective terms and applications, and try their best to follow along.

Hardware needed: Jetson Orin Nano, Desktop/Laptop with an internet connection and mobile hotspot capabilities
Software needed: Visual Studio Code, Web browser

1. Connect to your Jetson through VS Code using SSH (Make sure the Jetson is connected to your Desktop/Laptop's mobile hotspot)
2. In the "Explorer" section, create a folder for the application on your Jetson (ex. scavenger_app)

<img width="435" height="147" alt="image" src="https://github.com/user-attachments/assets/8b8e6827-5be6-4ca5-bd9e-a6851c12a791" />


3. Inside this folder, create two folders named "code" and "models" (case-sensitive)
4. Inside the "code" folder, make another folder named "templates"
5. Download app-v3.py, requirements.txt, and Dockerfile on your desktop/laptop and drag them into the "code" folder in the VS Code explorer (Dockerfile should have no extension)
6. Download index-v3.html into the "templates" folder in the VS Code explorer
7. Go to https://drive.google.com/file/d/1jLnXaLSxdoj2X8-nGSwbxKfQ4yKzVwEh/view?usp=sharing and download the .onnx file
8. Drag this .onnx file into the "models" folder in the VS Code explorer
9. Download labels.txt and put it into the "models" folder
10. You should now have app-v3.py, requirements.txt, and Dockerfile inside the "code" folder, index-v3.html inside the "templates" folder, and the .onnx file and labels.txt inside the "models" folder

<img width="369" height="1323" alt="image" src="https://github.com/user-attachments/assets/6c2c9ea0-96a3-45b3-aad6-b2ff80be9862" />


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
