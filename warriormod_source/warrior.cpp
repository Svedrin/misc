/* ======== warrior_mm ========
* Copyright (C) 2004-2005 Metamod:Source Development Team
* No warranties of any kind
*
* License: zlib/libpng
*
* Author(s): David "BAILOPAN" Anderson, Michael "MistaGee" Ziegler
* ============================
*/

#include <vector>
#include <sstream>
#include <oslink.h>
#include <Color.h>
#include "cvars.h"

#include "RecipientFilters.h"
#include <tier1/bitbuf.h>

#include "eventManager.h"
#include "versicheck.h"

#include "warrior_mm.h"

WarriorPlugin	g_WarriorPlugin;
MyListener	g_Listener;
GeeventManager	g_eventManager;
bool		g_VersionUp2date = false;
versicheck	g_versicheck;

PLUGIN_EXPOSE(WarriorPlugin, g_WarriorPlugin);

//This has all of the necessary hook declarations.  Read it!
#include "meta_hooks.h"


// VALVe ist einfach so *ARGH*
#undef INTERFACEVERSION_SERVERGAMEDLL
#define INTERFACEVERSION_SERVERGAMEDLL "ServerGameDLL004"


#define	FIND_IFACE(func, assn_var, num_var, name, type) \
	do { \
		if ( (assn_var=(type)((ismm->func())(name, NULL))) != NULL ) { \
			num = 0; \
			break; \
		} \
		if (num >= 999) \
			break; \
	} while ( num_var=ismm->FormatIface(name, sizeof(name)-1) ); \
	if (!assn_var) { \
		if (error) \
			snprintf(error, maxlen, "Could not find interface %s", name); \
		return false; \
	}

#define FStrEq(sz1, sz2) (strcmp((sz1), (sz2)) == 0)

#define IFSEARCH META_CONPRINTF("[WAR] Searching interface: %s", iface_buffer);
#define IFFOUND( address ) META_CONPRINTF(" - found at: 0x%x\n", address );


ConVar cvar_RoundCount(  "war_rounds", "12",
	FCVAR_NOTIFY, "Number of rounds to play", 1, 1, 488, 488);
ConVar cvar_FadeToBlack( "war_fadetoblack", "0",
	FCVAR_NOTIFY, "Value to set mp_fadetoblack to after loading ESL config", 0, 0, 1, 1);
ConVar cvar_Pausable(    "war_pausable", "0",
	FCVAR_NOTIFY, "Value to set sv_pausable to after loading ESL config", 0, 0, 1, 1);
ConVar cvar_AskReady(    "war_askRdyB4Live", "0",
	FCVAR_NOTIFY, "Should I ask \"rdy?\" once more before going Live?", 0, 0, 1, 1);
ConVar cvar_Record(      "war_record", "1",
	FCVAR_NOTIFY, "Enables / disables automatic demo recording. Requires tv_enable to be 1!!!", 0, 0, 1, 1);
ConVar cvar_ChPassword("war_changepassword", "0",
	FCVAR_NOTIFY, "Enables / disables automatic sv_password change on war start.", 0, 0, 1, 1);
ConVar cvar_bantime("war_bantime", "60",
	0, "Time people get banned - 0 for permanent, -1 for don't ban, else for timeban", -1, -1, 488, 488);

ConVar cvar_version("war_version", WARRIOR_VERSION,
	FCVAR_NOTIFY, "Version of WarriorMod Clanwar Manager", 0, 0, 488, 488);

ConVar cvar_mysql_host("war_mysql_host", "127.0.0.1", 0, "Host of MySQL server", 0, 0, 488, 488);
ConVar cvar_mysql_user("war_mysql_user", "root", 0, "Username for MySQL server", 0, 0, 488, 488);
ConVar cvar_mysql_pass("war_mysql_pass", "", 0, "Password for MySQL server", 0, 0, 488, 488);
ConVar cvar_mysql_db("war_mysql_db", "srcds", 0, "Database on MySQL server", 0, 0, 488, 488);
ConVar cvar_mysql_table("war_mysql_table", "wars", 0, "Table on MySQL server", 0, 0, 488, 488);
ConVar cvar_mysql_enable("war_mysql_enable", "0", 0, "Should I use MySQL at all?", 0, 0, 1, 1);

void ccmdHelpListener(){
	META_CONPRINT( "To start a war, type war_start into console. Then just see what happens ;)" );
	}
void ccmdLiveListener() 	{ g_eventManager.goLive(); }
void ccmdResetListener(){
	META_CONPRINT( "[WAR] Resetting plugin...\n" );
	g_eventManager.init_vars();
	}
void ccmdLiveListener2(){
	g_eventManager.init_vars();
	g_eventManager.rdy4Live( true );
	}
void ccmdKnifeListener()	{ g_eventManager.goKnife(); }
void ccmdStartListener(){
	g_eventManager.init_vars();
	g_eventManager.rdy4Knife();
	}
void ccmdBanTListener() 	{ g_eventManager.kickbanTeam( 2, cvar_bantime.GetInt() ); }
void ccmdBanCListener() 	{ g_eventManager.kickbanTeam( 3, cvar_bantime.GetInt() ); }
#ifdef _DeBuG
void ccmdListListener() 	{ g_eventManager.list_players();	}
void ccmdDebugListener()	{ g_eventManager.list_debug_info();	}
void ccmdGetUsersListener()	{ g_eventManager.findPlayerInfo();	}
void ccmdTeamNamesListener()	{ g_eventManager.findTeamNames();	}
void ccmdMaxplayersListener()	{ g_eventManager.serverActivate( 20 );	}
void ccmdMessagesListener(){
	if( g_eventManager.getServerGameDLL() == NULL ) return;
	char name[128] = "";
	int sizereturn = 0;
	bool boolrtn = false;
	for( int x=1; x < 27; x++ ){
		boolrtn = g_eventManager.getServerGameDLL()->GetUserMessageInfo( x, name, 128, sizereturn );
		META_CONPRINTF( "[WAR] Message %d = %s\n", x, name );
		}
	}
ConCommand cmd_UserMsgs( "war_messages", ccmdMessagesListener, "[DEBUG] Displays all existing user messages" );
ConCommand cmd_Maxplayers( "war_maxplayers", ccmdMaxplayersListener, "[DEBUG] Set maxplayers to 20" );
ConCommand cmd_Debug("war_debug", ccmdDebugListener, "[DEBUG] Display Debug information");
ConCommand cmd_List("war_list", ccmdListListener, "[DEBUG] Display internal user list");
ConCommand cmd_RefreshList("war_getusers", ccmdGetUsersListener, "[DEBUG] Refresh internal user list");
ConCommand cmd_TeamNames("war_teamnames", ccmdTeamNamesListener, "[DEBUG] Find the teams' names. Display using war_debug.");
#endif
ConCommand cmd_Help("war_help", ccmdHelpListener, "Display help on how to use the WarriorMod");
ConCommand cmd_Reset("war_reset", ccmdResetListener, "Reset plugin to defaults, deleting all stats and stuff");
ConCommand cmd_Live("war_go_live", ccmdLiveListener, "Do 3 restarts and go Live immediately, w/o asking ready");
ConCommand cmd_Knife("war_go_knife", ccmdKnifeListener, "Do 3 restarts and start a war at knife round, w/o asking ready");
ConCommand cmd_Start("war_start", ccmdStartListener, "Do 3 restarts and run a war, asking ready");
ConCommand cmd_Live2("war_live", ccmdLiveListener2, "Do 3 restarts and go Live, asking ready");
ConCommand cmd_BanT("war_kickban_t", ccmdBanTListener, "war_kickban_t: Kickban T team");
ConCommand cmd_BanC("war_kickban_ct", ccmdBanCListener, "war_kickban_ct: Kickban CT team");
void WarriorPlugin::ServerActivate( edict_t *pEdictList, int edictCount, int clientMax ){
	g_eventManager.serverActivate( clientMax );
	m_MaxPlayers = clientMax;
	}

void WarriorPlugin::ClientCommand( edict_t *pEntity ){
	RETURN_META( g_eventManager.clientCommand( pEntity, m_Engine -> Cmd_Argv(0), m_Engine -> Cmd_Args() ) );
	}

bool FireEvent_Handler( IGameEvent *event, bool bDontBroadcast ){
	if (!event || !event->GetName())
		RETURN_META_VALUE(MRES_IGNORED, false);
	
	const char *name = event->GetName();
	
	// Event - name - daten:
	// Rundenstart: round_start - int timelimit, fraglimit, string objective
	// chat: player_say - int userid, string text
	// teamchange / disconnect: player_team - int userid, team, oldteam, bool disconnect
	// treffer: "player_hurt" - int "userid", "attacker", "health", "armor", "weapon", "dmg_health" = "40", "dmg_armor", "hitgroup" = "1"
	// Rundenende: "round_end" - int "winner", reason, string message
	// Disconnect: "player_disconnect" - int "userid", string "reason", string "name", string "networkid"

	// Wir brauchen die Engine...
	IVEngineServer* m_Engine = g_WarriorPlugin.getEngine();
	
	if( FStrEq( name, "round_start") ){
		g_eventManager.roundStart();
		if( !g_VersionUp2date )
			META_CONPRINT( "[WAR] Your WarriorMod version is out of date. Please get the latest version from http://warriormod.extreme-gaming-clan.de!\n" );
		}
	else if(FStrEq( name, "round_end" ) )
		g_eventManager.roundEnd( event -> GetInt( "winner" ) );
	else if(FStrEq( name, "player_team" ) && !event -> GetBool( "disconnect" ))
		g_eventManager.playerTeam( event -> GetInt( "userid" ), event -> GetInt( "team" ), event -> GetInt( "oldteam" ) );
	else if(FStrEq( name, "player_disconnect"))
		g_eventManager.playerDisconnect( event -> GetInt( "userid" ), event -> GetString( "reason" ) );
	else if(FStrEq( name, "player_spawn"))
		g_eventManager.playerSpawn();
	else if(FStrEq( name, "round_freeze_end"))
		g_eventManager.roundFreezeEnd();
	else if( FStrEq( name, "weapon_fire" ) )
		g_eventManager.weaponFire( event -> GetInt( "userid" ), event -> GetString("weapon") );
	
	RETURN_META_VALUE(MRES_IGNORED, true);
	}

bool WarriorPlugin::Load( PluginId id, ISmmAPI *ismm, char *error, size_t maxlen, bool late ){
	PLUGIN_SAVEVARS();
#ifdef _DeBuG
	META_CONPRINT("[WAR] Loading plugin: WarriorMod (Debug compile)\n");
#else
	META_CONPRINT("[WAR] Loading plugin: WarriorMod\n");
#endif
	
	char iface_buffer[255];
	int num;
	
	// Get the interfaces we need
	strcpy(iface_buffer, INTERFACEVERSION_SERVERGAMEDLL);

	IFSEARCH
	FIND_IFACE(serverFactory, m_ServerDll, num, iface_buffer, IServerGameDLL *)
	IFFOUND( m_ServerDll );
	strcpy(iface_buffer, INTERFACEVERSION_VENGINESERVER);
	IFSEARCH
	FIND_IFACE(engineFactory, m_Engine, num, iface_buffer, IVEngineServer *)
	IFFOUND( m_Engine );
	strcpy(iface_buffer, INTERFACEVERSION_SERVERGAMECLIENTS);
	IFSEARCH
	FIND_IFACE(serverFactory, m_ServerClients, num, iface_buffer, IServerGameClients *)
	IFFOUND( m_ServerClients );
	strcpy(iface_buffer, INTERFACEVERSION_GAMEEVENTSMANAGER2);
	IFSEARCH
	FIND_IFACE(engineFactory, m_GameEventManager, num, iface_buffer, IGameEventManager2 *);
	IFFOUND( m_GameEventManager );
	strcpy(iface_buffer, INTERFACEVERSION_ISERVERPLUGINHELPERS);
	IFSEARCH
	FIND_IFACE(engineFactory, m_ServerPluginHelpers, num, iface_buffer, IServerPluginHelpers *);
	IFFOUND( m_ServerPluginHelpers );
	strcpy(iface_buffer, INTERFACEVERSION_PLAYERINFOMANAGER);
	IFSEARCH
	FIND_IFACE(serverFactory, m_PlayerInfoManager, num, iface_buffer, IPlayerInfoManager *);
	IFFOUND( m_PlayerInfoManager );
	strcpy(iface_buffer, INTERFACEVERSION_SERVERGAMEENTS);
	IFSEARCH
	FIND_IFACE(serverFactory, m_ServerEnts, num, iface_buffer, IServerGameEnts *);
	IFFOUND( m_ServerEnts );
	strcpy(iface_buffer, BASEFILESYSTEM_INTERFACE_VERSION);
	IFSEARCH
	FIND_IFACE(fileSystemFactory, m_BaseFileSystem, num, iface_buffer, IBaseFileSystem *);
	IFFOUND( m_BaseFileSystem );
	
	g_eventManager.setSMApi( g_SMAPI );
	g_eventManager.setEngineServer( m_Engine );
	g_eventManager.setServerGameDLL( m_ServerDll );
	g_eventManager.setPlayerInfoManager( m_PlayerInfoManager );
	
	EVM_SETCVAR( RoundCount );
	EVM_SETCVAR( FadeToBlack );
	EVM_SETCVAR( Pausable );
	EVM_SETCVAR( AskReady );
	EVM_SETCVAR( Record );
	EVM_SETCVAR( ChPassword );
	EVM_SETCVAR( mysql_host );
	EVM_SETCVAR( mysql_user );
	EVM_SETCVAR( mysql_pass );
	EVM_SETCVAR( mysql_db );
	EVM_SETCVAR( mysql_table );
	EVM_SETCVAR( mysql_enable );
	
	ismm -> AddListener(this, &g_Listener);

	//Init our cvars/concmds
	ConCommandBaseMgr::OneTimeInit(&g_Accessor);
	// g_Accessor is declared in cvars.h !

	//We're hooking the following things as POST, in order to seem like Server Plugins.
	//However, I don't actually know if Valve has done server plugins as POST or not.
	//Change the last parameter to 'false' in order to change this to PRE.
	//SH_ADD_HOOK_MEMFUNC means "SourceHook, Add Hook, Member Function".

	//Hook ServerActivate to our function
	SH_ADD_HOOK_MEMFUNC(IServerGameDLL, ServerActivate, m_ServerDll, &g_WarriorPlugin, &WarriorPlugin::ServerActivate, true);

	//The following functions are pre handled, because that's how they are in IServerPluginCallbacks

	//Hook ClientCommand to our function
	SH_ADD_HOOK_MEMFUNC(IServerGameClients, ClientCommand, m_ServerClients, &g_WarriorPlugin, &WarriorPlugin::ClientCommand, false);

	//This hook is a static hook, no member function
	SH_ADD_HOOK_STATICFUNC(IGameEventManager2, FireEvent, m_GameEventManager, FireEvent_Handler, false); 

	//Get the call class for IVServerEngine so we can safely call functions without
	// invoking their hooks (when needed).
	m_Engine_CC = SH_GET_CALLCLASS(m_Engine);

#if defined _DeBuG
	SH_CALL(m_Engine_CC, &IVEngineServer::LogPrint)("All hooks started!\n");
#endif
	g_SMAPI->AddListener(g_PLAPI, this);
	
	#ifndef WITH_MYSQL
	char versionstring[30];
	Q_snprintf( versionstring, 29, "%s NO MYSQL", WARRIOR_VERSION );
	cvar_version.SetValue( versionstring );
	#endif
	
	META_CONPRINT( "[WAR] Loaded successfully\n");
	META_CONPRINT( " * * * * * * * * * * * * * * * * * * * * * \n" );
	META_CONPRINT( " * WarriorMod - ClanWar manager          * \n" );
	META_CONPRINT( " * Idea, coding and testing by MistaGee  * \n" );
	META_CONPRINT( " * Thanx to the SourceMod dev team; I    * \n" );
	META_CONPRINT( " *  learned a lot from their code        * \n" );
	META_CONPRINT( " * Thanx to Mani who fixed my menus that * \n" );
	META_CONPRINT( " *  drove me crazy ;)                    * \n" );
	META_CONPRINT( " * Copyright (C) 2006 by MistaGee        * \n" );
	META_CONPRINT( " * -[ExTreME-gAmINg]- Ωωηξδ j00!         * \n" );
	META_CONPRINT( " * * * * * * * * * * * * * * * * * * * * * \n" );
	
	// Check if version is still up-2-date
	char* latestVersion = g_versicheck.getVersionFromServer();
	g_VersionUp2date = FStrEq( latestVersion, WARRIOR_VERSION );
	META_CONPRINTF("[WAR] Plugin version: %s - latest version available: %s\n", WARRIOR_VERSION, latestVersion );
	delete[] latestVersion;
	
	return true;
	}

bool WarriorPlugin::Unload(char *error, size_t maxlen)
{
	//IT IS CRUCIAL THAT YOU REMOVE CVARS.
	//As of Metamod:Source 1.00-RC2, it will automatically remove them for you.
	//But this is only if you've registered them correctly!

	//Make sure we remove any hooks we did... this may not be necessary since
	//SourceHook is capable of unloading plugins' hooks itself, but just to be safe.

	SH_REMOVE_HOOK_STATICFUNC(IGameEventManager2, FireEvent, m_GameEventManager, FireEvent_Handler, false); 
	SH_REMOVE_HOOK_MEMFUNC(IServerGameDLL, ServerActivate, m_ServerDll, &g_WarriorPlugin, &WarriorPlugin::ServerActivate, true);
	SH_REMOVE_HOOK_MEMFUNC(IServerGameClients, ClientCommand, m_ServerClients, &g_WarriorPlugin, &WarriorPlugin::ClientCommand, false);

	//this, sourcehook does not keep track of.  we must do this.
	SH_RELEASE_CALLCLASS(m_Engine_CC);

	return true;
	}

void WarriorPlugin::AllPluginsLoaded(){
	}

void *MyListener::OnMetamodQuery( const char *iface, int *ret ){
	if ( strcmp( iface, "WarriorPlugin" ) == 0 ){
		if ( ret )
			*ret = IFACE_OK;
		return static_cast<void *>( &g_WarriorPlugin );
		}

	if ( ret )
		*ret = IFACE_FAILED;
	return NULL;
	}
