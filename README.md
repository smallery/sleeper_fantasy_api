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

## Usage:
There are many uses for this repo, some examples are included in ./examples that you can run from the commandline:
For basic usage, getting user info:
```bash
python3 examples/example_basic_usage.py
```
For mode advanced usage gather user, league, draft, and player data:
```bash
python3 examples/example_advanced_usage.py
```
For basic to advanced usage of access the player database:
```bash
python3 examples/example_player_endpoint_search_queries.py
```

## Endpoints
The current endpoints available through the API are the following:

- **Draft Endpoint**:
  - `draft_endpoint`: Retrieve information about a draft (picks, users, trades) with a given draft_id.

- **League Endpoint**:
  - `league_endpoint`: Retrieve information on leagues with a given league_id.
  
- **Player Endpoint**:
  - `player_endpoint`: Retrieve the database of players from Sleeper along with key attributes.
  This endpoint has built in caching to store the player data locally to avoid excessive API calls.
  From current docs, it is expected to call the player_endpoint for all players more than once per day.
  
- **User Endpoint**:
  - `user_endpoint`: Retrieve information about a user using their username or user_id.

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
