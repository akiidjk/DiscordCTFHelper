# DiscordCTFHelper  
>
> A powerful and customizable bot to manage and organize CTF competitions on Discord.  

## Table of Contents  

- [DiscordCTFHelper](#discordctfhelper)
  - [Table of Contents](#table-of-contents)
  - [About](#about)
  - [Features](#features)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Steps](#steps)
  - [Usage](#usage)
  - [RAD](#rad)
  - [License](#license)
  - [Contact](#contact)

## About  

**DiscordCTFHelper** is a Python bot built with `discord.py` designed to streamline CTF (Capture The Flag) management on Discord servers. The bot integrates with CTFTime and provides essential features for tracking events, managing participants, and sharing updates.  

## Features  

- **Event Management**: Automatically fetch and display upcoming events from CTFTime.  
- **Participant Management**: Track team members and roles within CTFs.  
- **Notifications**: Send reminders for upcoming events and important milestones.  
- **Event Archive**: Organize past event details for reference.  
- **Customizable Status**: Display real-time bot activity.  

## Installation  

### Prerequisites  

- Python 3.12  
- `discord.py` (latest version)  
- A Discord bot token (obtainable via the [Discord Developer Portal](https://discord.com/developers/applications))  

### Steps  

1. Clone this repository:  

   ```bash  
   git clone https://github.com/akiidjk/DiscordCTFHelper.git  
   cd DiscordCTFHelper  
   ```  

2. Create a virtual environment:  

   ```bash  
   python3.12 -m venv venv  
   source venv/bin/activate  # On Windows: venv\Scripts\activate  
   ```  

3. Install dependencies:  

   ```bash  
   pip install -r requirements.txt  
   ```  

4. Set up your `.env` file:  
   Create a `.env` file in the root directory and include the following variables:  

   ```env  
   TOKEN=<discord_token>
   ```  

5. Run the bot:  

   ```bash  
   python bot.py  
   ```  

## Usage  

- Invite the bot to your server using the generated OAuth2 link from the [Discord Developer Portal](https://discord.com/developers/applications).  
- A user with admin role can run the command /init for the bot setup
- Create a ctf with /create_ctf

## RAD

- [Rad EN](/docs/RAD_en.pdf)
- [Rad IT](/docs/RAD_it.pdf)

## License  

This project is licensed under the Apache License. See the [LICENSE](LICENSE.md) file for details.  

## Contact  

For support or questions, feel free to open an issue or contact us directly
