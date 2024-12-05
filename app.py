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
    height = db.Column(db.String(10))

# Define the Team model
class Team(db.Model):
    team_name = db.Column(db.String(50), primary_key=True)
    city = db.Column(db.String(20))
    conference = db.Column(db.String(20))

# Home route
@app.route('/')
def home():
    players = Player.query.all()  # Retrieve all players
    return render_template('index.html', players=players)

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
        players_query = players_query.filter(Player.height == height_filter)

    players = players_query.all()

    # Get all distinct teams and positions for dropdowns
    teams = db.session.query(Team.team_name).all()
    positions = db.session.query(Player.position).distinct().all()

    return render_template('players.html', players=players, teams=teams, positions=positions,
                           team_filter=team_filter, position_filter=position_filter, height_filter=height_filter)

# Route to add a player
@app.route('/add', methods=['GET', 'POST'])
def add_player():
    if request.method == 'POST':
        name = request.form['name']
        team_name = request.form['team_name']
        position = request.form['position']
        height = request.form['height']

        new_player = Player(name=name, team_name=team_name, position=position, height=height)
        db.session.add(new_player)
        db.session.commit()
        flash('Player added successfully!')
        return redirect(url_for('players'))
    return render_template('add_player.html')

# Route to edit a player
@app.route('/edit_player/<int:player_id>', methods=['GET', 'POST'])
def edit_player(player_id):
    player = Player.query.get_or_404(player_id)
    
    if request.method == 'POST':
        player.name = request.form['name']
        player.team_name = request.form['team_name']
        player.position = request.form['position']
        player.height = request.form['height']
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

# Route for statistics
@app.route('/statistics', methods=['GET'])
def statistics():
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
        players_query = players_query.filter(Player.height == height_filter)

    players = players_query.all()

    # Calculate statistics
    average_height = None
    if players:
        total_height = sum([int(player.height.split("'")[0]) * 12 + int(player.height.split("'")[1]) for player in players if player.height])
        average_height = total_height / len(players)

    num_players = len(players)
    num_teams = len(set(player.team_name for player in players))

    # Get distinct teams for the filter dropdown
    teams = db.session.query(Team.team_name).all()

    return render_template('statistics.html', players=players, average_height=average_height, num_players=num_players, num_teams=num_teams,
                           teams=teams, team_filter=team_filter, position_filter=position_filter, height_filter=height_filter)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # This will create all the tables if they don't exist
    app.run(debug=True)
