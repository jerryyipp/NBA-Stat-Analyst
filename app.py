from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configure the SQLAlchemy Database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nba_stats.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'MyKey'  # Change this for production
db = SQLAlchemy(app)

# Define the Player model
class Player(db.Model):
    player_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    team_name = db.Column(db.String, db.ForeignKey('team.team_name'), nullable=False)
    position = db.Column(db.String(50))
    height = db.Column(db.Float)  # Store height as float (in inches)

# Define the Team model
class Team(db.Model):
    team_name = db.Column(db.String(50), primary_key=True)
    city = db.Column(db.String(20), nullable=False)
    conference = db.Column(db.String(20), nullable=False)

# Helper function to convert height in 'feet'inches' format to inches
def convert_height_to_inches(height):
    if height:
        feet_inches = height.split("'")
        if len(feet_inches) == 2:
            feet = int(feet_inches[0])
            inches = int(feet_inches[1].replace('"', ''))
            total_inches = feet * 12 + inches
            return total_inches
    return None

# Home route
@app.route('/')
def home():
    players = Player.query.all()  # Retrieve all players
    return render_template('index.html', players=players)

######################################################################
#                               PLAYERS                              #
######################################################################

# Players route with filtering
@app.route('/players', methods=['GET', 'POST'])
def players():
    # Get filter parameters from the request
    team_filter = request.args.get('team', '')
    position_filter = request.args.get('position', '')
    height_filter = request.args.get('height', '')

    # Build the query for filtering players
    players_query = Player.query

    if team_filter:
        players_query = players_query.filter(Player.team_name == team_filter)
    if position_filter:
        players_query = players_query.filter(Player.position == position_filter)
    if height_filter:
        players_query = players_query.filter(Player.height == float(height_filter))

    players = players_query.all()

    # Get all distinct teams and positions for dropdowns
    teams = db.session.query(Team.team_name).all()
    positions = db.session.query(Player.position).distinct().all()

    return render_template('players.html', players=players, teams=teams, positions=positions,
                           team_filter=team_filter, position_filter=position_filter, height_filter=height_filter)

# Route to add a player
@app.route('/add', methods=['GET', 'POST'])
def add_player():
    # Retrieve all teams to populate the dropdown
    teams = Team.query.all()

    if request.method == 'POST':
        name = request.form['name']
        team_name = request.form['team_name']
        position = request.form['position']
        height = request.form['height']

        # Convert height to inches if it's in a string format like '5'11"'
        height_in_inches = convert_height_to_inches(height)

        # Check if the team exists, if not assign "Free Agent"
        if not Team.query.filter_by(team_name=team_name).first():
            team_name = "Free Agent"

        new_player = Player(name=name, team_name=team_name, position=position, height=height_in_inches)
        db.session.add(new_player)
        db.session.commit()
        flash('Player added successfully!')
        return redirect(url_for('players'))

    return render_template('add_player.html', teams=teams)

# Route to edit a player
@app.route('/edit_player/<int:player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    
    if request.method == 'POST':
        player.name = request.form['name']
        player.team_name = request.form['team_name']
        player.position = request.form['position']
        height = request.form['height']

        # Convert height to inches if it's in a string format like '5'11"'
        player.height = convert_height_to_inches(height)
        
        db.session.commit()
        flash('Player updated successfully!')
        return redirect(url_for('players'))
    
    return render_template('edit_player.html', player=player)

# Route to delete a player
@app.route('/delete_player/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    player = Player.query.get_or_404(player_id)
    db.session.delete(player)
    db.session.commit()
    flash('Player deleted successfully!')
    return redirect(url_for('players'))

######################################################################
#                              END PLAYERS                           #
######################################################################

######################################################################
#                            STATISTICS                              #
######################################################################

# Route for statistics
@app.route('/statistics', methods=['GET'])
def statistics():
    team_filter = request.args.get('team', '')
    position_filter = request.args.get('position', '')
    height_filter = request.args.get('height', '')

    # Query distinct teams and positions for filter options
    teams = Team.query.order_by(Team.team_name).all()
    positions = db.session.query(Player.position).distinct().order_by(Player.position).all()
    positions = [pos[0] for pos in positions if pos[0]]  # Extract position values

    # Build the base query for filtering players
    query = Player.query
    if team_filter:
        query = query.filter(Player.team_name == team_filter)
    if position_filter:
        query = query.filter(Player.position == position_filter)
    if height_filter:
        query = query.filter(Player.height == float(height_filter))

    players = query.all()

    # Calculate additional statistics
    num_players = len(players)
    num_teams = Team.query.count()
    average_height = db.session.query(db.func.avg(Player.height)).scalar()

    # Average Height by Team
    average_height_by_team = db.session.query(
        Player.team_name,
        db.func.avg(Player.height).label('avg_height')
    ).group_by(Player.team_name).all()

    # Position Breakdown
    position_breakdown = db.session.query(
        Player.position,
        db.func.count(Player.player_id).label('num_players')
    ).group_by(Player.position).all()

    return render_template(
        'statistics.html',
        teams=teams,
        positions=positions,
        players=players,
        num_players=num_players,
        num_teams=num_teams,
        average_height=average_height,
        average_height_by_team=average_height_by_team,
        position_breakdown=position_breakdown,
        team_filter=team_filter,
        position_filter=position_filter,
        height_filter=height_filter
    )

######################################################################
#                            END STATISTICS                          #
######################################################################

######################################################################
#                                 TEAMS                              #
######################################################################

@app.route('/teams', methods=['GET', 'POST'])
def teams():
    if request.method == 'POST':
        team_name = request.form['team_name']
        city = request.form['city']
        conference = request.form['conference']

        new_team = Team(team_name=team_name, city=city, conference=conference)
        db.session.add(new_team)
        db.session.commit()
        flash('Team added successfully!')
        return redirect(url_for('teams'))

    teams = Team.query.all()
    return render_template('teams.html', teams=teams)


@app.route('/edit_team/<string:team_name>', methods=['GET', 'POST'])
def edit_team(team_name):
    team = Team.query.get_or_404(team_name)

    if request.method == 'POST':
        team.city = request.form['city']
        team.conference = request.form['conference']
        db.session.commit()
        flash('Team updated successfully!')
        return redirect(url_for('teams'))

    return render_template('edit_team.html', team=team)


@app.route('/delete_team/<string:team_name>', methods=['POST'])
def delete_team(team_name):
    team = Team.query.get_or_404(team_name)
    db.session.delete(team)
    db.session.commit()
    flash('Team deleted successfully!')
    return redirect(url_for('teams'))


######################################################################
#                            END TEAMS                               #
######################################################################

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # This will create all the tables if they don't exist
    app.run(debug=True)
