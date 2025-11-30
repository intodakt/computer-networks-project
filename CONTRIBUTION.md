Team Contribution Report

Project Name: Network Whiteboard Application
Team Members:

[Member 1 Name] (Student ID)

[Member 2 Name] (Student ID)

[Member 3 Name] (Student ID)

[Member 4 Name] (Student ID)

Summary of Contributions

[Member 1 Name]

Role: Server Architect & Threading Lead

Server Core: Designed the multithreaded server architecture (whiteboard_server.py) using Python's threading module to handle concurrent client connections.

Synchronization: Implemented thread locks (clients_lock, history_lock) to prevent race conditions when accessing shared resources like the client list and drawing history.

Connection Management: Handled the client handshake process, including the initial JOIN protocol and robust disconnect handling.

[Member 2 Name]

Role: Protocol Designer & Network Logic

Protocol Specification: Designed the custom application-layer protocol for drawing commands (DRAW, LINE, RECT, CIRCLE, TRI), chat messages (CHAT), and system commands (CLEAR, USER_LIST).

Broadcast Logic: Implemented the broadcast() function on the server to relay messages to all other clients efficiently.

Network Integration: Wrote the network communication logic in the client (receive_messages loop) to parse incoming protocol strings and trigger the appropriate GUI actions.

[Member 3 Name]

Role: Client GUI Lead & Tool Implementation

GUI Framework: Built the main graphical user interface using tkinter, including the layout with the toolbar, canvas, and sidebar.

Drawing Tools: Implemented the drawing logic for the Brush and Eraser tools, including the "smooth drawing" algorithm (line interpolation) to fix gaps in fast mouse movements.

Shape Tools: Developed the logic for shape previews and final drawing for Lines, Rectangles, Circles, and Triangles.

[Member 4 Name]

Role: Feature Developer & User Experience

Chat System: Developed the complete chat feature, including the sidebar UI, input handling, and message display logic.

User List: Implemented the real-time "Online Users" list, updating the sidebar whenever a user joins or leaves.

History Sync: Implemented the server-side history storage and the client-side logic to receive and replay the full drawing history upon joining.

Testing & Documentation: Conducted testing across multiple machines and wrote the README.md file with setup instructions.

Code Ownership Breakdown

File

Primary Author

Secondary Contributor

whiteboard_server.py

[Member 1 Name]

[Member 2 Name]

whiteboard_client.py

[Member 3 Name]

[Member 4 Name]

README.md

[Member 4 Name]

[All Members]

Peer Review Statement

We confirm that all team members contributed equally to the project's success. We met regularly to discuss the protocol design, divide tasks, and debug connectivity issues together.
