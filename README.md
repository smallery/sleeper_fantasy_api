# sleeper_fantasy_api

An object-oriented Python wrapper for the [Sleeper Fantasy Football API](https://docs.sleeper.com/), designed to simplify working with data on users, leagues, transactions, and more.

The Sleeper API is currently read-only.

H/T to other repos who created similar functions before me:
- [sleeper-api-wrapper](https://github.com/dtsong/sleeper-api-wrapper)
- [sleeper-py](https://github.com/AdamCurtisVT/sleeper-py)

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Endpoints](#endpoints)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Overview
This project simplifies accessing the Sleeper API, allowing users to easily fetch player stats, league data, transactions, and more in an object-oriented manner. The wrapper supports complex queries using `AND` and `OR` logic, with a focus on easy integration and flexibility.

## Features
- Fetching player stats, leagues, and transactions.
- Supports advanced player search logic (e.g., `AND`/`OR` conditions).
- Object-oriented design for ease of use and integration.
  
Planned features:
- Custom setting of CONVERT_RESULT global variable by user
- Change samples to be able to be run through the command-line

## Installation
To install locally, follow these steps:

### Prerequisites:
- Python 3.10

### Installation:
```bash
git clone https://github.com/smallery/sleeper_fantasy_api.git
cd sleeper_fantasy_api
pip install -r requirements.txt
```

## Endpoints
The current endpoints available through the API are the following:

- **Draft Endpoint**:
  - `draft_endpoint`: .

- **League Endpoint**:
  - `league_endpoint`: .
  
- **Player Endpoint**:
  - `player_endpoint`: Retrieve the database of players from Sleeper along with key attributes.
  
- **User Endpoint**:
  - `user_endpoint`: .

For more details, refer to the full [Sleeper API documentation](https://docs.sleeper.com/#introduction).

## Contributing
Contributions are welcome! Please follow the guidelines below:
- Fork the repository.
- Create a new branch (`git checkout -b githubUsername/feature-branch`).
- Submit a pull request.

## License
This project is licensed under the MIT License. See the `LICENSE` file for more information.

## Contact
If you have any questions or issues, please contact [Sam Mallery](mailto:sleeperfantasyapi@gmail.com).
