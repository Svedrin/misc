/* ======== warrior_mm ========
* Copyright (C) 2006 Michael Ziegler
* No warranties of any kind
*
* License: zlib/libpng
*
* Author(s): Michael "MistaGee" Ziegler
* ============================
*/

#include <cstdlib>
#include <ctime>
#include <vector>
#include <sstream>
#include <oslink.h>
#include <tier1/bitbuf.h>

#include <ISmmPlugin.h>
#include <igameevents.h>

//#include <mysql/mysql.h>

#include <dlls/iplayerinfo.h>
#include "RecipientFilters.h"

#include "lang.h"
#include "eventManager.h"

#define EVM_CONPRINT	if(m_SMAPI) m_SMAPI->ConPrint
#define EVM_CONPRINTF	if(m_SMAPI) m_SMAPI->ConPrintf

#define DO_NOTHING   0
#define DO_ANI_LIVE  1
#define DO_ANI_KNIFE 2

#define TEAM_NONE 0
#define TEAM_SPEC 1
#define TEAM_T    2
#define TEAM_CT   3
#define TEAMNAME( index ) ( index == 0 ? "NONE" : ( index == 1 ? "SPEC" : ( index == 2 ? "T" : "CT" ) ) )

#define isCharacter( zeichen ) ( ( zeichen >= '0' && zeichen <= '9' ) || ( zeichen >= 'a' && zeichen <= 'z' ) || ( zeichen >= 'A' && zeichen <= 'Z' ) )
#define isSignificantCharacter( zeichen ) ( zeichen == '-' || zeichen == '_' || zeichen == '<' || zeichen == '>' || zeichen == '{' || zeichen == '}' || zeichen == '[' || zeichen == ']' || zeichen == '|' )

#define WEAPON_DROP_SCRIPT "alias wa20 \"wait; wait; wait; wait; wait; wait; wait; wait; wait; wait; wait; wait; wait; wait; wait; wait; wait; wait; wait; wait\"; alias waffenweg \"slot1; wait; drop; wait; slot2; wait; drop; wait; slot5; wait; wait; drop; wa20\"; waffenweg; waffenweg; waffenweg; waffenweg; waffenweg\n"

#define FStrEq(sz1, sz2) (strcmp((sz1), (sz2)) == 0)
#define FStrEqi(sz1, sz2) (stricmp((sz1), (sz2)) == 0)
#define empty( string ) ( strlen( string ) == 0 )

#ifndef min
#define min(a,b) ((a) < (b) ? (a) : (b))
#endif
#ifndef max
#define max(a,b) ((a) > (b) ? (a) : (b))
#endif
#ifndef border
#define border(wert, lower, upper) ( min( max( wert, lower ), upper ) )
#endif
#ifndef abs
#define abs(x) ( (x < 0) ? (-x) : (x) )
#endif

#define FOREACHVALIDPLAYER(var) for(int var = 0; var < 32; var++) if(m_playerInfo[var] != NULL)

#define IN_WAR ( m_KnifeRound || m_Live )
#define RDY ( !m_WaitingForReady_T && !m_WaitingForReady_CT )

#define CHECK_POINTERS( returnvalue ) if( m_SMAPI == NULL || m_Engine == NULL || m_PlayerInfoManager == NULL ) return returnvalue;

#define MYSQL_CRE8_TABLE "CREATE TABLE IF NOT EXISTS `%s` (\
	`timestamp` int(11) NOT NULL PRIMARY KEY,\
	`name_team1` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,\
	`name_team2` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,\
	`kniferoundwinner` int(3) NOT NULL,\
	`score_t1_firstround` int(5) NOT NULL,\
	`score_t2_firstround` int(5) NOT NULL,\
	`score_t1_total` int(5) NOT NULL,\
	`score_t2_total` int(5) NOT NULL,\
	`map` varchar(20) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,\
	`demo` int(5) NOT NULL,\
	`teamsize` int(5) NOT NULL\
	)"
	
#define MYSQL_INSERT_VALUES "INSERT INTO %s VALUES( '%d', '%s', '%s', '%d', '%d', '%d', '%d', '%d', '%s', '%d', '%d' )"

#define MYSQL_CRE8_PLAYERS "CREATE TABLE IF NOT EXISTS `%s_players` (\
	`timestamp` int(11) NOT NULL,\
	`team` int(5) NOT NULL,\
	`name` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,\
	PRIMARY KEY ( `timestamp`, `name` )\
	)"
	
#define MYSQL_INSERT_PLAYERS "INSERT INTO %s_players VALUES ( '%d', '%d', '%s' )"

GeeventManager::GeeventManager(){
	m_SMAPI = NULL;
	m_Engine = NULL;
	m_newPass = NULL;
	m_PlayerInfoManager = NULL;
	for( int i = 0; i < 32; i++ )
		m_playerInfo[i] = NULL;
	}

void GeeventManager::OneTimeInit(){
	init_vars();
	
#ifdef WITH_MYSQL
	if( !cvar_mysql_enable -> GetBool() ) return;
	m_mysql = new MYSQL();
	mysql_init( m_mysql );
	
	if( mysql_real_connect( m_mysql, cvar_mysql_host -> GetString(), cvar_mysql_user -> GetString(),
		cvar_mysql_pass -> GetString(), cvar_mysql_db -> GetString(), 0, NULL, 0 ) )
		EVM_CONPRINT( "[WAR] MySQL Connection established\n" );
	else{	EVM_CONPRINTF( "[WAR] Error connecting to MySQL server:\n%s\n", mysql_error( m_mysql ) ); return; }
	
	EVM_CONPRINT( "[WAR] Creating table if it doesn't exist already\n" );
	char cmd[2048];
	strPrune( cmd, 2048 );
	Q_snprintf( cmd, 2047, MYSQL_CRE8_TABLE, cvar_mysql_table -> GetString() );
	if( mysql_query( m_mysql, cmd ) ){
		EVM_CONPRINTF( "[WAR] Error creating wars table:\n%s\n", mysql_error( m_mysql ) );
		}
	strPrune( cmd, 512 );
	Q_snprintf( cmd, 2047, MYSQL_CRE8_PLAYERS, cvar_mysql_table -> GetString() );
	if( mysql_query( m_mysql, cmd ) ){
		EVM_CONPRINTF( "[WAR] Error creating players table:\n%s\n", mysql_error( m_mysql ) );
		}
#endif
	}

GeeventManager::~GeeventManager(){
	if( m_newPass )
		delete[] m_newPass;
#ifdef WITH_MYSQL
	mysql_close( m_mysql );
	delete m_mysql;
	m_mysql = NULL;
#endif
	// Ich hatte hier mal drin dass m_playerInfo[] geloescht werden soll. Das mag der Server aber nicht!!!
	}

META_RES GeeventManager::clientCommand( edict_t* uEntity, const char* command, const char* args ){
	CHECK_POINTERS( MRES_IGNORED );
// 	MRES_IGNORED    = plugin didn't take any action
// 	MRES_HANDLED    = plugin did something, but real function should still be called
// 	MRES_OVERRIDE   = call real function, but use my return value
// 	MRES_SUPERCEDE  = skip real function; use my return value

	const int uID = m_Engine -> GetPlayerUserId( uEntity );
	const int uTeam = m_PlayerInfoManager -> GetPlayerInfo( uEntity ) -> GetTeamIndex();
	
	if( FStrEq( command, "war_name" ) ){
		for( int i = 0; i < 2; i++ )
			if( !m_TeamNameSetByUser[i] ){
				m_TeamNameSetByUser[i] = uID;
				strPrune( m_DesiredTeamNames[i], 256 );
				strcpy( m_DesiredTeamNames[i], args );
				m_DesiredTeamNames[i][255] = 0;
				char cmd[256];
				Q_snprintf(cmd, 255, LANG_TEAMNAMEHASBEENSET, m_DesiredTeamNames[i] );
				m_Engine -> ClientPrintf( uEntity, cmd );
				
				break;
				}
			else if( findPlayerTeam( m_TeamNameSetByUser[i] ) == uTeam ){
				char cmd[256];
				Q_snprintf(cmd, 255, LANG_TEAMNAMEALREADYSET,
					findPlayerName( m_TeamNameSetByUser[i] ), m_DesiredTeamNames[i] );
				m_Engine -> ClientPrintf( uEntity, cmd );
				
				break;
				}
		return MRES_SUPERCEDE;
		}
	else if( FStrEq( command, "joinclass" ) ){
#ifdef _DeBuG
		EVM_CONPRINT( "[WAR] Client selected skin\n" );
#endif
		if( IN_WAR && m_TeamChangesRemaining == 1 ) goLive();
		m_TeamChangesRemaining = max( 0, m_TeamChangesRemaining - 1 );
		}
	else if( FStrEq( command, "menuselect" ) ){
		// Checken ob wir grade auf ein Team warten das rdy werden muss
		if( FStrEq( args, "1" ) && m_WaitingForReady_T && findPlayerTeam( uID ) == TEAM_T){
			m_WaitingForReady_T = false;
			if( m_KnifeRound )	rdy4Knife();
			else			rdy4Live();
			}
		else if( FStrEq( args, "1" ) && m_WaitingForReady_CT && findPlayerTeam( uID ) == TEAM_CT){
			m_WaitingForReady_CT = false;
			if( m_KnifeRound )	rdy4Knife();
			else			rdy4Live();
			}
		// Checken ob grade einer STAY/LEAVE angekuendigt hat
		// Wichtig: Team checken, damit nich irgendwelche 1337-H4xx0r-Scriptkiddies per "menuselect x"@konsole faken
		else if( m_TeamToSayStayLeave == findPlayerTeam( uID ) && FStrEq( args, "1" ) ){
			// STAY
			m_Engine -> ServerCommand( "say \"[---S-T-A-Y---]\"\n" );
			m_WaitingForReady_T = m_WaitingForReady_CT = cvar_AskReady -> GetBool();
			m_LastKnifeRoundWinner = m_TeamToSayStayLeave - 1;
			m_TeamToSayStayLeave = 0;
			rdy4Live();
			}
		else if( m_TeamToSayStayLeave == findPlayerTeam( uID ) && FStrEq( args, "2" ) ){
			// LEAVE
			forceTeamChange();
			m_TeamChangesRemaining = findPlayerCount();
			m_Engine -> ServerCommand( "say \"[---L-E-A-V-E---]\"\n" );
			m_LastKnifeRoundWinner = 4 - m_TeamToSayStayLeave;
			m_TeamToSayStayLeave = 0;
			}
		else if( m_TeamToSayStayLeave && m_TeamToSayStayLeave != findPlayerTeam( uID ) ){
			char cmd[256];
			Q_snprintf( cmd, 255, LANG_STFUFAKER, findPlayerName( uID ) );
			m_Engine -> ServerCommand( cmd );
			}
		}
	else if( FStrEq( command, "jointeam" ) ){
		// Wenn keine Teamchanges erwartet werden, akzeptieren wir auch keine!
		// Es sei denn der Typ hat grade erst gejoint...
		if( IN_WAR && RDY && !m_TeamChangesRemaining && uTeam > 0 ){
			m_Engine -> ClientPrintf( uEntity, LANG_NOTEAMCHANGEALLOWED );
			return MRES_SUPERCEDE;
			}
		else	return MRES_IGNORED;
		}
#ifdef _DeBuG
	//EVM_CONPRINTF("[WAR] Client %d issued command %s %s.\n", uID, command, args );
#endif
	return MRES_IGNORED;
	}

const char* GeeventManager::getRandomString( const int len ){
	if( !len ) return NULL;
	time_t timeviech;
	time( &timeviech );
	srandom( (int)timeviech );		// Damit wird's bestimmt nie zweimal gleich initialisiert ;)
	
	char* ergebnis = new char[ len + 1 ];	// Len zeichen + 0
	for( int i = 0; i < len; i++ ){
		char zufallszahl = 0;
		// Sicherstellen dass die Zufallszahl stimmt und nicht 3 Wochen braucht um berechnet zu werden
		// dazu einfach den Fehlerbereich so klein wie moeglich halten (47 + 75 = 122 -> zahl immer zw 47 und 125)
		while( !isCharacter( zufallszahl ) )
			zufallszahl = (char)( ( random() % 75 ) + 47 );
		ergebnis[i] = zufallszahl;
		}
	ergebnis[ len ] = 0; // Fuer ein korrektes Ende sorgen...
	return ergebnis;
	}

void GeeventManager::rdy4Live( bool overrideCvar ){
	findPlayerInfo();
	m_OverrideCvar = overrideCvar;
	if( !checkTeamSizes() ){
		EVM_CONPRINT( LANG_NOOPPONENTS );
		return;
		}
	m_KnifeRound = false;
	m_Live = true;
	
	do_config();
	
	if( ( m_WaitingForReady_T || m_WaitingForReady_CT ) && ( cvar_AskReady -> GetBool() || m_OverrideCvar ) )
		displayGetReadyMsg();
	else	goLive();
	}

void GeeventManager::rdy4Knife(){
	findPlayerInfo();
	if( !checkTeamSizes() ){
		EVM_CONPRINT( LANG_NOOPPONENTS );
		return;
		}
	m_KnifeRound = true;
	do_config();
	if( m_WaitingForReady_T || m_WaitingForReady_CT )
		displayGetReadyMsg();
	else	goKnife();
	}

void GeeventManager::goLive(){
	findPlayerInfo();
	m_OverrideCvar = false;
	if( !checkTeamSizes() ){
		EVM_CONPRINT( LANG_NOOPPONENTS );
		return;
		}
	m_RoundsPlayed = 0;
	m_KnifeRound = false;
	m_Live = true;
	
	do_config();
	
	m_TeamChangesRemaining = 0;
	m_WaitingForReady_T = m_WaitingForReady_CT = false;
	
	if( !m_TeamsHaveBeenChanged ){
		m_TeamScores[0] = 0;
		m_TeamScores[1] = 0;
		findTeamNames();
		}
	else{
		m_TeamScores[0] = m_TeamScoresAtTeamChange[0];
		m_TeamScores[1] = m_TeamScoresAtTeamChange[1];
		}
	
	do_config();
	
	m_RestartsRemaining = 2;
	
	m_AfterRestartsDo = DO_ANI_LIVE;
	m_Engine -> ServerCommand( LANG_LIVEAFTER3RR );
	}

void GeeventManager::goKnife(){
	findPlayerInfo();
	if( !checkTeamSizes() ){
		EVM_CONPRINT( LANG_NOOPPONENTS );
		return;
		}
	
	m_KnifeRound = true;
	m_RestartsRemaining = 2;
	m_AfterRestartsDo = DO_ANI_KNIFE;
	
	m_WaitingForReady_T = m_WaitingForReady_CT = false;
	
	findTeamNames();
	do_config();
	
	m_Engine -> ServerCommand( "bot_knives_only" );
	
	m_Engine -> ServerCommand( LANG_KNIFEAFTER3RR );
	}

bool GeeventManager::checkTeamSizes(){
	// Return false if one team is empty
	bool terrs_vorhanden = false;
	bool cts_vorhanden = false;
	FOREACHVALIDPLAYER(i){
		if(      m_playerInfo[i] -> GetTeamIndex() == TEAM_T  ) terrs_vorhanden = true;
		else if( m_playerInfo[i] -> GetTeamIndex() == TEAM_CT ) cts_vorhanden   = true;
		}
	return ( terrs_vorhanden && cts_vorhanden );
	}

void GeeventManager::findPlayerInfo(){
	CHECK_POINTERS();
#if defined _DeBuG
	EVM_CONPRINT( "[WAR] Refreshing user list...\n" );
#endif
	for ( int i = 0; i < m_MaxPlayers; ++i ){
		edict_t *player = m_Engine -> PEntityOfEntIndex( i + 1 );
		if( !player || player->IsFree() || !player->GetUnknown() || !player->GetUnknown()->GetBaseEntity() )
			m_playerInfo[i] = NULL;
		else
			m_playerInfo[i] = m_PlayerInfoManager -> GetPlayerInfo( player );
		}
	}

int GeeventManager::findPlayerCount( bool CountSpectators ){
	int plCount = 0;
	FOREACHVALIDPLAYER( i )
		if( m_playerInfo[i] -> GetTeamIndex() > 1 ||			// Specs zaehlen meist nich
		    m_playerInfo[i] -> GetTeamIndex() > 0 && CountSpectators )  // Spawnende aber nie
			plCount++;
	return plCount;
	}

int GeeventManager::findPlayerIndex( int uid ){
	FOREACHVALIDPLAYER( i )
		if( m_playerInfo[i] -> GetUserID() == uid )
			return i;
	return -1;
	}

const char* GeeventManager::findPlayerName( int uid ){
	int plIndex = findPlayerIndex( uid );
	if( plIndex != -1 )
		return m_playerInfo[plIndex] -> GetName();
	else	return NULL;
	}

int* GeeventManager::findTeamMemberCount(){
	int* retVal = new int[2];
	FOREACHVALIDPLAYER(i)
		retVal[ border( m_playerInfo[i] -> GetTeamIndex() - 2 , 0, 1 ) ]++;
	return retVal;
	}

edict_t* GeeventManager::findPlayerEnt( int uid ){
	CHECK_POINTERS( NULL );
	int plIndex = findPlayerIndex( uid );
	if( plIndex != -1 )
		return m_Engine -> PEntityOfEntIndex( plIndex + 1 );
	else	return NULL;
	}

int GeeventManager::findPlayerTeam( int uid ){
	int plIndex = findPlayerIndex( uid );
	if( plIndex != -1 )
		return m_playerInfo[plIndex] -> GetTeamIndex();
	else	return 0;
	}

void GeeventManager::forceTeamChange(){
	FOREACHVALIDPLAYER(i){
		// Den Clients folgenden Befehl senden:
		// "jointeam %d", <bei CTs: 2, bei Ts: 3>
		m_Engine -> ClientCommand( m_Engine -> PEntityOfEntIndex( i + 1 ), "jointeam %d\n",
			5 - m_playerInfo[i] -> GetTeamIndex() );
		}
	}

void GeeventManager::init_vars(){
#ifdef _DeBuG
	EVM_CONPRINT( "[WAR] Init\n" );
#endif
	m_TeamScores[0] = m_TeamScores[1] = m_TeamScoresAtTeamChange[0] = m_TeamScoresAtTeamChange[1] = 0;
	m_TeamNameSetByUser[0] = m_TeamNameSetByUser[1] = 0;
	strPrune( m_TeamNames[0], 256 );        strPrune( m_TeamNames[1], 256 );
	strPrune( m_DesiredTeamNames[0], 256 ); strPrune( m_DesiredTeamNames[1], 256 );
	m_RestartsRemaining = 0;
	m_AfterRestartsDo = DO_NOTHING;
	m_TeamChangesRemaining = 0;
	if( cvar_RoundCount ) m_Rounds2Play = cvar_RoundCount -> GetInt();
#ifdef _DeBuG
	else EVM_CONPRINT( "[WAR] Could not read cvar_RoundCount due to NULL pointer.\n" );
#endif
	if( m_newPass ){
		delete[] m_newPass;
		m_newPass = NULL;
		}
	m_TeamToSayStayLeave = m_LastKnifeRoundWinner = 0;
	m_RoundsPlayed = 0;
	m_OverrideCvar         = false;
	m_WaitingForReady_T    = true;
	m_WaitingForReady_CT   = true;
	m_TeamsHaveBeenChanged = false;
	m_KnifeRound           = false;
	m_Live                 = false;
	m_SaidMajorityThingy   = false;
	m_ConfigHasBeenDone    = false;
	if( cvar_Record != NULL && cvar_Record -> GetBool() )
		m_Engine -> ServerCommand( "tv_stoprecord\n" );
	m_Engine -> ServerCommand( "bot_all_weapons\n" );
	}

void GeeventManager::do_config(){
	CHECK_POINTERS();
	if( m_ConfigHasBeenDone ) return;
	m_ConfigHasBeenDone = true;
	// ESL-Config laden
	switch( border( findPlayerCount() / 2, 1, 5 ) ){
		case 1: m_Engine -> ServerCommand( "exec esl1on1.cfg\n" ); break;
		case 2: m_Engine -> ServerCommand( "exec esl2on2.cfg\n" ); break;
		case 3: m_Engine -> ServerCommand( "exec esl3on3.cfg\n" ); break;
		case 4:
		case 5: m_Engine -> ServerCommand( "exec esl5on5.cfg\n" ); break;
		}
	// FTB setzen und anzeigen, Pausable setzen, War Mode einschalten
	char cmd[256];
	Q_snprintf( cmd, 255, "mp_fadetoblack %d; say \"[---FTB IS %s---]\"; sv_pausable %d; ma_war 1\n",
		 cvar_FadeToBlack -> GetBool(),
		(cvar_FadeToBlack -> GetBool() ? "ON" : "OFF" ),
		 cvar_Pausable -> GetBool() );
	m_Engine -> ServerCommand( cmd );
	
	if( cvar_ChPassword -> GetBool() ){
		// Passwort zufallsgenerieren
		if( m_newPass )
			delete[] m_newPass;
		m_newPass = getRandomString( 8 );
		Q_snprintf( cmd, 255, "say \"[---PW IS %s---]\"; sv_password \"%s\"\n", m_newPass, m_newPass );
		m_Engine -> ServerCommand( cmd );
		}
	
	// Nu: Checken ob aufgenommen werden soll, wenn ja tu das Judas
	// Wird einfach mal angenommen dass der Server mit tv_enable 1 gestartet wurde.
	// Wenn tv_enable 0 nimmt er halt nix auf, Pech gehabt...
	if( cvar_Record -> GetBool() ){
		char demoname[100];
		const char* mapname = m_SMAPI -> pGlobals() -> mapname.ToCStr();
		if( empty( m_TeamNames[0] ) || empty( m_TeamNames[1] ) ) findTeamNames();
		time_t timeviech;
		time( &timeviech );
		m_TimeStamp = (int)timeviech;

		Q_snprintf( demoname, 99, LANG_DEMONAME, m_TeamNames[0], m_TeamNames[1],
			mapname, m_TimeStamp );
		//strPruneInvalidChars( demoname, 99 );
		Q_snprintf( cmd, 255, LANG_RECORDINGDEMO, demoname, demoname );
		m_Engine -> ServerCommand( cmd );
		}
	
	}

void GeeventManager::strPrune( char* s, int len ){
	for( int i = 0; i < len; i++ )
		s[i] = 0;
	}

void GeeventManager::strPruneInvalidChars( char* string, int len ){
	// Alles was nicht normal ist durch ein _ ersetzen
	for( int i = 0; i < len; i++ )
		if( !isCharacter( string[i] ) && string[i] != '-' )
			string[i] = '_';
	}

void GeeventManager::trim( char* string ){
	int len = strlen( string );
	char* result = new char[ len ];
	strPrune( result, len );
	
	// Find how far we may copy
	for( int i = len - 1; i >= 0; i-- )
		if( string[i] == ' ' || string[i] == '\t' || string[i] == '\n' )
			string[i] = 0;
		else	break;
	len = strlen( string );
	
	if( len ){
		// Copy
		bool NoMoreFrontSpaces = false;
		int resultPos = 0;
		for( int i = 0; i <= len; i++ )
			if( ( string[i] != ' ' && string[i] != '\t' ) || NoMoreFrontSpaces ){
				result[ resultPos ] = string[i];
				NoMoreFrontSpaces = true;
				resultPos++;
				}
		}
	// Now write results into string...
	strPrune( string, len );
	strcpy( string, result );
	delete[] result;
	}

char* GeeventManager::findLongestMatch( const char* s1, const char* s2 ){
	// Aufgabe: Laengste Uebereinstimmung zw. S1 und S2 finden
	// z.b. s1 = "-[ExTreME-gAmINg]-", s2 = "<->[ExTreME-gAmINg]<->" sollte [ExTreME-gAmINg] und nicht - ausgeben ;)
	int s1Len = strlen(s1), s2Len = strlen(s2), s1Pos = 0, s2Pos = 0;
	
	// Ein genuegend grosses Ergebnis bereitstellen...
	char* ergebnis  = new char[ max( s1Len, s2Len ) ]; int  ergLen = 0,  ergPos = 0;
	char* vergebnis = new char[ max( s1Len, s2Len ) ]; int vergLen = 0, vergPos = 0;
	
	strPrune(  ergebnis, max( s1Len, s2Len ) );
	strPrune( vergebnis, max( s1Len, s2Len ) );
	
	// Erstmal s1 mit s2 vergleichen.
	for( s1Pos = 0; s1Pos < s1Len; s1Pos++ ){
		if( s2Pos >= s2Len ) s2Pos = 0; // Nicht zuviel lesen...
		// Solange S1 = S2 einfach in verg kopieren, die Posis dabei inkrementieren
		if( s1[ s1Pos ] == s2[ s2Pos ] ) vergebnis[ vergPos++ ] = s2[ s2Pos++ ];
		else if( vergLen = strlen( vergebnis ) ){// Vergleich hat nur Sinn wenn ein vErgebnis gefunden wurde...
			// s1 != s2, also ist _dieser_ Vergleich abgeschlossen
			// jetzt muss das verg mit dem bisherigen erg verglichen werden.
			// Wenn erg kuerzer ist als verg, ueberschreiben, sonst verg vergessen.
			if( vergLen > ergLen ){
				strPrune( ergebnis, ergLen );
				strcpy( ergebnis, vergebnis );
				ergLen = vergLen;
				}
			strPrune( vergebnis, vergLen );
			vergLen = vergPos = 0;
			}
		}
	// Nochmal init...
	strPrune( vergebnis, vergLen );
	vergLen = vergPos = s1Pos = s2Pos = 0;
	// nu muss derselbe Vergleich umgekehrt gemacht werden...
	for( s2Pos = 0; s2Pos < s2Len; s2Pos++ ){
		if( s1Pos >= s1Len ) s1Pos = 0; // Nicht zuviel lesen...
		// Solange S1 = S2 einfach in verg kopieren, die Posis dabei inkrementieren
		if( s1[ s1Pos ] == s2[ s2Pos ] ) vergebnis[ vergPos++ ] = s1[ s1Pos++ ];
		else if( vergLen = strlen( vergebnis ) ){
			if( vergLen > ergLen ){
				strPrune( ergebnis, ergLen );
				strcpy( ergebnis, vergebnis );
				ergLen = vergLen;
				}
			strPrune( vergebnis, vergLen );
			vergLen = vergPos = 0;
			}
		}
	delete[] vergebnis;	// Aufraeumen...
#ifdef _DeBuG
	EVM_CONPRINTF( "[WAR] Vergleiche \"%s\" mit \"%s\" - Ergebnis: \"%s\".\n", s1, s2, ergebnis );
#endif
	return ergebnis;
	}

void GeeventManager::findTeamNames(){
// 	Vorgehensweise:
// 	1. ersten Namen als Vergleichsstring nehmen
// 	2. mit dem zweiten Namen vergleichen, Gemeinsamkeiten finden
// 	3. Gemeinsamkeiten in den Vergleichsstring kopieren, Rest rausschmeissen
// 	4. mit dem naechsten Namen vergleichen -> goto 3.
// 	
// 	Beispiel:
// 	-[ExTreME-gAmINg]-MistaGee
// 	-[ExTreME-gAmINg]-Dark Reaver
// 	-[ExTreME-gAmINg]-nethead
// 	-[ExTreME-gAmINg]-Doomhammer
// 	-[ExTreME-gAmINg]-painkiller
// 	
// 	setze Vergleichsstring:		-[ExTreME-gAmINg]-MistaGee
// 	Vergleiche mit:			-[ExTreME-gAmINg]-Dark Reaver
// 	Finde neuen Vergleichsstring:	-[ExTreME-gAmINg]-
// 	Vergleiche mit:			-[ExTreME-gAmINg]-nethead
// 	Finde neuen Vergleichsstring:	-[ExTreME-gAmINg]-
// 	Vergleiche mit:			-[ExTreME-gAmINg]-Doomhammer
// 	Finde neuen Vergleichsstring:	-[ExTreME-gAmINg]-
// 	Vergleiche mit:			-[ExTreME-gAmINg]-painkiller
// 	Finde neuen Vergleichsstring:	-[ExTreME-gAmINg]-
// 	
// 	Teamname = -[ExTreME-gAmINg]-.
	
	bool TeamNameHasBeenSet[2];
	TeamNameHasBeenSet[0] = TeamNameHasBeenSet[1] = false;
	
	// Erstmal checken ob nicht schon ein Name festgelegt wurde...
	for( int i = 0; i < 2; i++ )
		if( m_TeamNameSetByUser[i] ){
			// Wer war es und welchem Team gehoert der jetzt an? Dessen Name muss gesetzt werden!
			const int uTeam = findPlayerTeam( m_TeamNameSetByUser[i] ) - 2;
			strPrune( m_TeamNames[ uTeam ], 256 );
			strcpy( m_TeamNames[ uTeam ], m_DesiredTeamNames[i] );
			m_TeamNames[uTeam][255] = 0;
			TeamNameHasBeenSet[ uTeam ] = true;
			}
	
	for( int currentTeam = 0; currentTeam <= 1; currentTeam++ ){
		if( TeamNameHasBeenSet[ currentTeam ] ) continue;
		char compare[256];
		strPrune( compare, 256 );
		bool firstNameWasCopied = false;
		for( int currentPlayerIndex = 0; currentPlayerIndex < 32; currentPlayerIndex++ ){
			// Dies ist kein Mitglied des aktuellen Teams
			if( !m_playerInfo[ currentPlayerIndex ] ||
			     m_playerInfo[ currentPlayerIndex ] -> GetTeamIndex() != currentTeam + 2 ) continue;
			const char* plName = m_playerInfo[ currentPlayerIndex ] -> GetName();
			// Ersten Namen kopieren
			if( !firstNameWasCopied ){
				strcpy( compare, plName );
				compare[255] = 0;
				firstNameWasCopied = true;
				continue;
				}
			// Den aktuellen Namen mit compare vergleichen...
			const char* compared = findLongestMatch( plName, compare );
			strPrune( compare, 256 );
			strcpy( compare, compared );
			compare[255] = 0;
			
			delete[] compared;
			}
		strPrune( m_TeamNames[ currentTeam ], 256 );
		if( !empty( compare ) ){
			strcpy( m_TeamNames[ currentTeam ], compare );
			m_TeamNames[ currentTeam ][255] = 0;
			trim( m_TeamNames[ currentTeam ] );
			}
		
		// If no name could be found, use Team1 / Team2
		if( empty( m_TeamNames[ currentTeam ] ) || strlen( m_TeamNames[ currentTeam ] ) < 3 )
			Q_snprintf( m_TeamNames[ currentTeam ], 255, "Team%d", currentTeam + 1 );
		
#if defined _DeBuG
		EVM_CONPRINTF( "[WAR] Speichere m_TeamNames[ currentTeam = %d ] = \"%s\"\n", currentTeam, m_TeamNames[ currentTeam ] );
#endif
		}
	}

#ifdef _DeBuG
void GeeventManager::list_players(){
	EVM_CONPRINT("[WAR] Displaying user list...\n");
	//const char* mapname = m_SMAPI -> pGlobals() -> mapname.ToCStr();
	FOREACHVALIDPLAYER( i )
		EVM_CONPRINTF( "[WAR] Slot = %d | UID = %d | Team = %d (%s) | Name = %s\n", i,
			m_playerInfo[i] -> GetUserID(),
			m_playerInfo[i] -> GetTeamIndex(), TEAMNAME( m_playerInfo[i] -> GetTeamIndex() ), 
			m_playerInfo[i] -> GetName() );
	}

void GeeventManager::list_debug_info(){
	EVM_CONPRINTF( "[WAR] m_RoundsPlayed = %d\n",		m_RoundsPlayed );
	
	if( cvar_RoundCount )
		EVM_CONPRINTF( "[WAR] m_Rounds2Play / CVar = %d, %d\n", m_Rounds2Play, cvar_RoundCount -> GetInt() );
	else	EVM_CONPRINTF( "[WAR] m_Rounds2Play / CVar = %d, ? \n[WAR] Could not read cvar_RoundCount due to NULL pointer.\n",
			m_Rounds2Play );
		
	EVM_CONPRINTF( "[WAR] m_TeamScores = %d, %d\n",		m_TeamScores[0], m_TeamScores[1] );
	EVM_CONPRINTF( "[WAR] m_TeamScoresAtTeamChange = %d, %d\n", m_TeamScoresAtTeamChange[0],
		m_TeamScoresAtTeamChange[1] );

	EVM_CONPRINTF( "[WAR] m_TeamNames = %s, %s\n",		m_TeamNames[0], m_TeamNames[1]);
	EVM_CONPRINTF( "[WAR] m_TeamNameSetByUser = %d, %d\n",	m_TeamNameSetByUser[0], m_TeamNameSetByUser[1] );
	EVM_CONPRINTF( "[WAR] m_DesiredTeamNames = %s, %s\n",	m_DesiredTeamNames[0], m_DesiredTeamNames[1] );
	
	if( cvar_AskReady )
		EVM_CONPRINTF("[WAR] m_WaitingForReady_T/CT/CVar = %d, %d, %d\n",
			m_WaitingForReady_T, m_WaitingForReady_CT, cvar_AskReady -> GetBool() );
	else	EVM_CONPRINTF(
		"[WAR] m_WaitingForReady_T/CT/CVar = %d, %d, ? \n[WAR] Could not read cvar_AskReady due to NULL pointer.\n",
			m_WaitingForReady_T, m_WaitingForReady_CT );
	
	EVM_CONPRINTF( "[WAR] m_KnifeRound = %d\n",		m_KnifeRound );
	EVM_CONPRINTF( "[WAR] m_Live = %d\n",			m_Live );
	EVM_CONPRINTF( "[WAR] m_TeamsHaveBeenChanged = %d\n",	m_TeamsHaveBeenChanged );
	EVM_CONPRINTF( "[WAR] m_TeamToSayStayLeave = %d\n",	m_TeamToSayStayLeave );
	EVM_CONPRINTF( "[WAR] m_TeamChangesRemaining = %d\n",	m_TeamChangesRemaining );
	EVM_CONPRINTF( "[WAR] m_SaidMajorityThingy = %d\n",	m_SaidMajorityThingy );
	EVM_CONPRINTF( "[WAR] m_newPass = %s\n",		m_newPass );
	EVM_CONPRINTF( "[WAR] m_MaxPlayers = %d\n",		m_MaxPlayers );
	EVM_CONPRINTF( "[WAR] m_OverrideCvar = %d\n",		m_OverrideCvar );
	}
#endif

void GeeventManager::kickbanTeam( int team, int time ){
	findPlayerInfo();
	FOREACHVALIDPLAYER(i){
		if( m_playerInfo[i] -> GetTeamIndex() == team ){
			char cmd[256];
			if( time == -1 )
				Q_snprintf( cmd, 255, "kickid %s Kicked by Admin\n",
					m_playerInfo[i] -> GetNetworkIDString() );
			else
				Q_snprintf( cmd, 255, "banid %d %d; kickid %s Kicked and banned by Admin\n",
					time,
					m_playerInfo[i] -> GetUserID(),
					m_playerInfo[i] -> GetNetworkIDString() );
			m_Engine -> ServerCommand( cmd );
			}
		}
	findPlayerInfo();
	}


void GeeventManager::displayGetReadyMsg(){
	CHECK_POINTERS();
	if ( !IN_WAR || ( m_Live && !cvar_AskReady -> GetBool() && !m_OverrideCvar ) )
		return;
	// Checken ob eins der Teams komplett aus Bots besteht - wenn ja, sind die rdy
	bool TsAreBotsOnly = true, CTsAreBotsOnly = true;
	FOREACHVALIDPLAYER(i){
		if( m_playerInfo[i] -> GetTeamIndex() == TEAM_T && !m_playerInfo[i] -> IsFakeClient())
			TsAreBotsOnly = false;
		if( m_playerInfo[i] -> GetTeamIndex() == TEAM_CT && !m_playerInfo[i] -> IsFakeClient())
			CTsAreBotsOnly = false;
		}
	if( TsAreBotsOnly  ) m_WaitingForReady_T  = false;
	if( CTsAreBotsOnly ) m_WaitingForReady_CT = false;
	
	// Menue anzeigen, das nach rdy? fragt und noch ein paar Stats anzeigt
	short allowedkeys = ( (1<<0) | (1<<9) );
	
	char menubody[512];
	Q_snprintf(menubody, 511, LANG_MENUBODY_NRDY,
		( m_WaitingForReady_T           ? LANG_NOT  : "" ),
		( m_WaitingForReady_CT          ? LANG_NOT  : "" ),
		m_Rounds2Play,
		( cvar_FadeToBlack -> GetBool() ? LANG_ON   : LANG_OFF ),
		( cvar_Pausable -> GetBool()    ? LANG_ON   : LANG_OFF ),
		( cvar_Record -> GetBool()      ? LANG_YES  : LANG_NO ),
		( cvar_ChPassword -> GetBool()  ? m_newPass : LANG_UNCHANGED ),
		( m_Live                        ? "LIVE"    : "KNIFE ROUND" ) );
	
	char menubody_rdy[512];
	Q_snprintf(menubody_rdy, 511, LANG_MENUBODY_RDY,
		( m_WaitingForReady_T           ? LANG_NOT  : "" ),
		( m_WaitingForReady_CT          ? LANG_NOT  : "" ),
		m_Rounds2Play,
		( cvar_FadeToBlack -> GetBool() ? LANG_ON   : LANG_OFF ),
		( cvar_Pausable -> GetBool()    ? LANG_ON   : LANG_OFF ),
		( cvar_Record -> GetBool()      ? LANG_YES  : LANG_NO ),
		( cvar_ChPassword -> GetBool()  ? m_newPass : LANG_UNCHANGED ),
		( m_Live                        ? "LIVE"    : "KNIFE ROUND" ) );
	
	CRFGeneral* rf_rdy = new CRFGeneral();
	
	CRFGeneral* rf_nrdy = new CRFGeneral();
	FOREACHVALIDPLAYER(i){
		if( ( m_WaitingForReady_T  && m_playerInfo[i] -> GetTeamIndex() == TEAM_T  ) ||
		    ( m_WaitingForReady_CT && m_playerInfo[i] -> GetTeamIndex() == TEAM_CT ) )
			rf_nrdy -> AddPlayer( i + 1 );
		else	rf_rdy  -> AddPlayer( i + 1 );
		}
	
	ClassicMenu( rf_rdy, 0, 30, menubody_rdy );
	
	ClassicMenu( rf_nrdy, allowedkeys, 30, menubody );
	}

void GeeventManager::serverActivate( int clientMax ){
	OneTimeInit();
	findPlayerInfo();
	m_MaxPlayers = clientMax;
	}

void GeeventManager::playerDisconnect( int uID, const char* reason ){
	findPlayerInfo();
	if( IN_WAR && m_playerInfo[ findPlayerIndex( uID ) ] -> IsPlayer() && FStrEqi( reason, "Disconnect by user." ) ){
		// Wenn ein Team komplett raus is, War abbrechen
		int* memberCount = findTeamMemberCount();
		if( !memberCount[0] || !memberCount[1] ){
			char cmd[256];
			Q_snprintf(cmd, 255, LANG_WARCANCELLED,
				( memberCount[0] > memberCount[1] ? m_TeamNames[1] : m_TeamNames[0] ) );
			m_Engine -> ServerCommand( cmd );
			
			init_vars();
			}
		}
	}

void GeeventManager::playerTeam( int uID, int newTeam, int oldTeam ){
	CHECK_POINTERS();
	// Player is zu faul leave zu sagen, er macht einfach
	if( m_KnifeRound && m_TeamToSayStayLeave == findPlayerTeam( uID ) ){
		forceTeamChange();
		m_Engine -> ServerCommand( "say \"[---L-E-A-V-E---]\"\n" );
		m_TeamChangesRemaining = findPlayerCount();
		m_TeamToSayStayLeave = 0;
		}
	if(m_TeamChangesRemaining == 1 && ( m_TeamsHaveBeenChanged || m_KnifeRound ) ){
		m_WaitingForReady_T = m_WaitingForReady_CT = cvar_AskReady -> GetBool();
		rdy4Live();
		}
	findPlayerInfo();
#if defined _DeBuG
	EVM_CONPRINTF( "[WAR] User switched from Team %s to %s.\n", TEAMNAME( oldTeam ), TEAMNAME( newTeam ) );
#endif
	}

void GeeventManager::playerSpawn(){
	CHECK_POINTERS();
	float ThisSpawn = m_Engine -> Time();
	// Check how long ago the last player spawned to avoid mess at round start
	if( ThisSpawn - m_LastSpawn < 0.5 )
		return;
	m_LastSpawn = ThisSpawn;
	if( m_RestartsRemaining > 0 ){
		m_Engine -> ServerCommand( "mp_restartgame 1\n" );
		char cmd[256];
		Q_snprintf( cmd, 255, "say \"[---#%d---]\"\n", 3 - m_RestartsRemaining );
		m_Engine -> ServerCommand( cmd );
		m_RestartsRemaining--;
		}
	else if(m_AfterRestartsDo){
		m_Engine -> ServerCommand( "say \"[---#3---]\"\n" );
		if( m_AfterRestartsDo == DO_ANI_LIVE )
			m_Engine -> ServerCommand( "exec ani_live.cfg\n" );
		else if( m_AfterRestartsDo == DO_ANI_KNIFE ){
			m_Engine -> ServerCommand( "exec ani_knife.cfg\n" );
			FOREACHVALIDPLAYER( i ){
				// Alle Spieler sollen ihre Waffen entsorgen, also Script rueberschicken
				m_Engine -> ClientCommand( m_Engine -> PEntityOfEntIndex( i + 1 ), WEAPON_DROP_SCRIPT );
				}
			}
		m_AfterRestartsDo = DO_NOTHING;
		}
	}

void GeeventManager::weaponFire( int uID, const char* uWeapon ){
	CHECK_POINTERS();
	if(!FStrEq( uWeapon, "knife" ) && m_KnifeRound && RDY && !m_TeamToSayStayLeave ){
		m_Engine -> ClientCommand( findPlayerEnt( uID ), "kill\n" );
		char cmd[256];
		Q_snprintf( cmd, 255, LANG_PLAYERSLAYEDINKNIFE, findPlayerName( uID ), uWeapon );
		m_Engine -> ServerCommand( cmd );
		}
	}

void GeeventManager::roundStart(){
	CHECK_POINTERS();
	if( !RDY )
		displayGetReadyMsg();
	else if( !m_RestartsRemaining && !m_AfterRestartsDo && m_Live ){
		char cmd[256];
		// Berechnen wieviele Runden bereits gezockt wurden.
		// Falls die Teams gewechselt wurden, muessen die vorher gespielten Runden abgezogen werden...
		m_RoundsPlayed = m_TeamScores[0] + m_TeamScores[1] + 1 -
			( ( m_TeamsHaveBeenChanged && !m_TeamChangesRemaining ) ? m_Rounds2Play : 0 );
		if( m_RoundsPlayed < m_Rounds2Play )
			Q_snprintf( cmd, 255, LANG_ROUNDSCORE, m_RoundsPlayed, m_Rounds2Play,
				m_TeamNames[0], ( m_TeamsHaveBeenChanged ? "CT" : "T" ),  m_TeamScores[0],
				m_TeamNames[1], ( m_TeamsHaveBeenChanged ? "T"  : "CT" ), m_TeamScores[1] );
		else if( m_RoundsPlayed == m_Rounds2Play )
			Q_snprintf( cmd, 255, LANG_LASTROUNDSCORE,
				m_TeamNames[0], ( m_TeamsHaveBeenChanged ? "CT" : "T" ),  m_TeamScores[0],
				m_TeamNames[1], ( m_TeamsHaveBeenChanged ? "T"  : "CT" ), m_TeamScores[1] );
		else if( m_TeamsHaveBeenChanged && !m_TeamChangesRemaining ){
			if( m_TeamScores[0] > m_TeamScores[1] )
				Q_snprintf( cmd, 255, LANG_CTWINSWAR, m_TeamNames[0], m_TeamScores[0], m_TeamScores[1] );
			else if( m_TeamScores[0] < m_TeamScores[1] )
				Q_snprintf( cmd, 255, LANG_TWINSWAR, m_TeamNames[1], m_TeamScores[1], m_TeamScores[0] );
			else	Q_snprintf( cmd, 255, LANG_DRAW, m_TeamScores[1], m_TeamScores[0] );
			init_vars();
			m_Engine -> ServerCommand( "ma_war 0\n" );
			}
		else{
			Q_snprintf( cmd, 255, LANG_TEAMCHANGE, m_TeamNames[0], m_TeamScores[0], m_TeamNames[1], m_TeamScores[1] );
			if( !m_TeamsHaveBeenChanged ){
				m_TeamChangesRemaining      = findPlayerCount();
				m_TeamScoresAtTeamChange[0] = m_TeamScores[0];
				m_TeamScoresAtTeamChange[1] = m_TeamScores[1];
				forceTeamChange();
				}
			m_TeamsHaveBeenChanged = true;
			}
		m_Engine -> ServerCommand( cmd );
		}
	}

void GeeventManager::roundEnd( int winner ){
	CHECK_POINTERS();
	if( m_Live && RDY ){
		if ( winner <= 1 ){ // EVM_CONPRINT enthaelt ein if(), daher muessen hier die {} gesetzt sein damit's geht!
			EVM_CONPRINT( "[WAR] Round end, draw - no-one scores.\n" );
			}
		else if( winner >= 4 ){
			EVM_CONPRINT( "[WAR] Round end, E-R-R-O-R - score is not counted!\n" );
			}
#ifdef _DeBuG
		else if( !m_TeamsHaveBeenChanged && m_RoundsPlayed <= m_Rounds2Play ){
			EVM_CONPRINTF( "[WAR] Round end, %s (%s) wins and now has won %d rounds.\n",
				m_TeamNames[ border( winner - 2, 0 , 1 ) ], TEAMNAME( winner),
				++m_TeamScores[ border( winner - 2, 0 , 1 ) ] );
			}
		else if( m_RoundsPlayed <= m_Rounds2Play ){
			EVM_CONPRINTF( "[WAR] Round end, %s (%s) wins and now has won %d rounds.\n",
				m_TeamNames[ !border( winner - 2, 0 , 1 ) ], TEAMNAME( winner),
				++m_TeamScores[ !border( winner - 2, 0 , 1 ) ] );
			}
#else
		else if( !m_TeamsHaveBeenChanged && m_RoundsPlayed <= m_Rounds2Play )
			++m_TeamScores[ border( winner - 2, 0 , 1 ) ] ;
		else if( m_RoundsPlayed <= m_Rounds2Play )
			++m_TeamScores[ !border( winner - 2, 0 , 1 ) ] ;
#endif
		else	m_Engine -> ServerCommand( LANG_TEAMCHANGE_NOTCOUNTED );
		// Vllt hat ja einer grade gewonnen?
		for( int i = 0; i < 2; i++ )	// »nur« die Mehrheit der Runden
			if( m_TeamScores[i] == m_Rounds2Play + 1 && !m_SaidMajorityThingy ){
				char cmd[256];
				Q_snprintf( cmd, 255, LANG_WONMAJORITY, m_TeamNames[i] );
				m_Engine -> ServerCommand( cmd );
				m_SaidMajorityThingy = true;
				}
		
		if( m_RoundsPlayed == m_Rounds2Play && m_TeamsHaveBeenChanged ){ // Endgueltig den War
			char cmd[256];
			if( m_TeamScores[0] > m_TeamScores[1] )
				Q_snprintf(cmd, 255, LANG_CTWINSWAR, m_TeamNames[0], m_TeamScores[0], m_TeamScores[1] );
			else if(m_TeamScores[0] < m_TeamScores[1])
				Q_snprintf(cmd, 255, LANG_TWINSWAR,  m_TeamNames[1], m_TeamScores[1], m_TeamScores[0] );
			else	Q_snprintf(cmd, 255, LANG_DRAW, m_TeamScores[1], m_TeamScores[0] );
			m_Engine -> ServerCommand( cmd );
			
#ifdef WITH_MYSQL
			if( cvar_mysql_enable -> GetBool() && m_mysql != NULL ){
				strPrune( cmd, 256 );
				Q_snprintf( cmd, 255, MYSQL_INSERT_VALUES, cvar_mysql_table -> GetString(),
					m_TimeStamp, m_TeamNames[0], m_TeamNames[1], m_LastKnifeRoundWinner,
					m_TeamScoresAtTeamChange[0], m_TeamScoresAtTeamChange[1], m_TeamScores[0],
					m_TeamScores[1], m_SMAPI -> pGlobals() -> mapname.ToCStr(), cvar_Record -> GetBool(),
					border( findPlayerCount() / 2, 1, 5 ) );
				if( mysql_query( m_mysql, cmd ) )
					EVM_CONPRINTF( "[WAR] Error inserting result to MySQL:\n%s\n", mysql_error(m_mysql));
				
				FOREACHVALIDPLAYER(i){
					if( m_playerInfo[i] -> GetTeamIndex() < 2 )
						continue;
					strPrune( cmd, 256 );
					char plEscName[40];
					strPrune( plEscName, 40 );
					int plNameLen = strlen( m_playerInfo[i] -> GetName() );
					mysql_real_escape_string( m_mysql, plEscName, m_playerInfo[i] -> GetName(), plNameLen );
					Q_snprintf( cmd, 255, MYSQL_INSERT_PLAYERS, cvar_mysql_table -> GetString(),
						m_TimeStamp, 4 - m_playerInfo[i] -> GetTeamIndex(),
						plEscName );
					if( mysql_query( m_mysql, cmd ) )
						EVM_CONPRINTF( "[WAR] Error inserting player %s to MySQL:\n%s\n",
							m_playerInfo[i] -> GetName(), mysql_error(m_mysql) );
					}
				}
#endif
			}
		}
	else if( m_KnifeRound && RDY ){
		if ( winner <= 1 ){
			EVM_CONPRINT( "[WAR] Round end, draw - no-one wins.\n" );
			}
		else if( winner >= 4 ){
			EVM_CONPRINT( "[WAR] Round end, E-R-R-O-R!\n" );
			}
		else{
			// Ansagen wer gewonnen hat, nach stay or leave fragen, wenns gesagt wurde 3rr -> live
			char cmd[256];
			if( !m_TeamToSayStayLeave )
				m_TeamToSayStayLeave = winner;
			Q_snprintf( cmd, 255, LANG_WINSKNIFE, TEAMNAME(m_TeamToSayStayLeave), TEAMNAME(m_TeamToSayStayLeave) );
			m_Engine -> ServerCommand( cmd );
			m_Engine -> ServerCommand( "bot_all_weapons" );

			// Menue anzeigen, mit dem der Gewinner seinen Wunsch nach Stay/Leave aeussern kann...
			short allowedkeys = ( (1<<0) | (1<<1) );
			const char* menubody = "->1. stay\n->2. leave\n\n";
			
			CRFGeneral* rf = new CRFGeneral();
			FOREACHVALIDPLAYER(i)
				if( m_playerInfo[i] -> GetTeamIndex() == m_TeamToSayStayLeave )
					rf -> AddPlayer( i + 1 );
			ClassicMenu( rf, allowedkeys, 30, menubody ); // Der loescht den rf gleich
			}
		}
	}

void GeeventManager::roundFreezeEnd(){
	CHECK_POINTERS();
	if( !RDY && IN_WAR ){
#ifdef GERMAN
		m_Engine -> ServerCommand( "say \"[---MistaGees ClanWar-Manager bereit - GL&HF---]\"\n" );
#else
		m_Engine -> ServerCommand( "say \"[---MistaGee's ClanWar manager running - GL&HF---]\"\n" );
#endif
		m_Engine -> ServerCommand( LANG_NAMEYOURTEAM );
		}
	}

void GeeventManager::ClassicMenu( int id, int allowedkeys, int time, const char *menubody ){
	CRFGeneral* rf = NULL;
	if ( id == 0 )
		rf = MakeRfAllPlayers();
	else{
		rf = new CRFGeneral();
		rf -> AddPlayer( id );
		}
	
	ClassicMenu( rf, allowedkeys, time, menubody );
	}

void GeeventManager::ClassicMenu( edict_t* pEntity, int allowedkeys, int time, const char *menubody ){
	CRFGeneral* rf = NULL;
	if ( !pEntity )
		rf = MakeRfAllPlayers();
	else{
		rf = new CRFGeneral();
		rf -> AddPlayer( pEntity );
		}
	
	ClassicMenu( rf, allowedkeys, time, menubody );
	}

void GeeventManager::ClassicMenu( CRFGeneral* rf, int allowedkeys, int time, const char *menubody ){
	// Geklaut von SourceMod
	if( !rf || !rf -> GetRecipientCount() ) return;

	// Usermessages have a limited size (thanks to Mani for pointing this out!)
	const int BUFSIZE = 240;
	char buf[ BUFSIZE + 1 ];
	char empty[1];
	empty[0] = 0;
	const int iShowMenu = UserMessageIndex( "ShowMenu" );
	if(iShowMenu <= 0) return;
	
	do{
		strncpy( buf, menubody, BUFSIZE );
		buf[ BUFSIZE ] = 0;
		menubody += strlen( buf );
		
		bf_write *msg = m_Engine -> UserMessageBegin( rf, iShowMenu );
		msg -> WriteWord( allowedkeys );
		msg -> WriteChar( ( time > 127 ? -1 : time ) );
		msg -> WriteByte( (*menubody ? true : false) );
		msg -> WriteString( buf );
		msg -> WriteString( empty );
		m_Engine -> MessageEnd();
		} while( *menubody );
	delete rf;
	rf = NULL;
	}

int GeeventManager::UserMessageIndex( const char *messageName ){
	if( m_ServerDll == NULL )
		return -2;
	char name[128] = "";
	int sizereturn = 0;
	bool boolrtn = false;
	for( int x=1; x < 27; x++ ){
		boolrtn = m_ServerDll->GetUserMessageInfo( x, name, 128, sizereturn );
		if( name && FStrEq( messageName, name ) ){
			return x;
			}
		}
	return -1;
	}

CRFGeneral* GeeventManager::MakeRfAllPlayers(){
	CRFGeneral* ergebnis = new CRFGeneral();
	FOREACHVALIDPLAYER(i)
		ergebnis -> AddPlayer( i + 1 );
	return ergebnis;
	}
