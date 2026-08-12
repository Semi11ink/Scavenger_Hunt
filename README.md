# Scavenger_Hunt
This is my NVIDIA project. It is an application that runs a flask app on the local network that allows multiple people to play a scavenger hunt game on multiple devices. The objective is to find whatever object the game tells you to find, and the game will know if you found it using an object detection model.

---------------------INSTALLATION INSTRUCTIONS---------------------

These are installations instructions for people who have a Windows desktop or laptop and uses Windows terminology and applications. Mac and Linux users will have to find their respective terms and applications, and try their best to follow along.

Hardware needed: Jetson Orin Nano, Desktop/Laptop with an internet connection and mobile hotspot capabilities
Software needed: Visual Studio Code, Web browser

1. Connect to your Jetson through VS Code using SSH (Make sure the Jetson is connected to your Desktop/Laptop's mobile hotspot)
2. In the "Explorer" section, create a folder for the application (ex. scavenger_app)
3. Inside this folder, create two folders named "code" and "models" (case-sensitive)
4. Inside the "code" folder, make another folder named "templates"
5. Download app-v3.py, requirements.txt, and Dockerfile on your desktop/laptop and drag them into the "code" folder in the VS Code explorer (Dockerfile should have no extension)
6. Download index-v3.html into the "templates" folder in the VS Code explorer
7. Go to https://drive.google.com/file/d/1jLnXaLSxdoj2X8-nGSwbxKfQ4yKzVwEh/view?usp=sharing and download the .onnx file
8. Drag this .onnx file into the "models" folder in the VS Code explorer
9. Download labels.txt and put it into the "models" folder
10. You should now have app-v3.py, requirements.txt, and Dockerfile inside the "code" folder, index-v3.html inside the "templates" folder, and the .onnx file and labels.txt inside the "models" folder
NOTE: These files should be on your Jetson. We are just using VS Code to see what files are on your Jetson
11. In the Jetson terminal in VS Code, use "cd" to move into the "code" folder (ex. "cd scavenger_app/code")
12. Run this command in the Jetson terminal in VS Code: "docker build -t my-jetson-app ." (Yes, the period at the end is included.)
13. Run this command: "docker run -it --runtime nvidia --network host -v $(pwd)/..:/app my-jetson-app"
14. When the docker container opens, enter "cd code"
15. Enter "python3 app-v3.py"
16. You should see lots of stuff come up in the terminal, but at the end you should see "Running on all addresses (0.0.0.0)", "Running on https://127.0.0.1:5000", "Running on https://(your jetson's ip address)", and "Press CTRL+C to quit"
17. To play the game, go into your web browser and type in "https://jetson-ip:5000" (replace jetson-ip with your jetson's ip address)

18. If you don't know how to find your jetson's ip address, follow these steps:
19. Open settings
20. Click Network & internet
21. Click Mobile hotspot
22. Your Jetson should be connected to your hotspot. If it is, look at the bottom of the "Properties" Section and you should see the devices connected and their names
23. Your Jetson's name should be something like nvidia-desktop if you didn't change it
24. The IP address of the jetson should be next to its name
