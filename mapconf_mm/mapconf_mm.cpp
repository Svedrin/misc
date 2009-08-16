/* ======== Mapconf_mm ========
* Copyright (C) 2004-2005 Metamod:Source Development Team
* No warranties of any kind
*
* License: zlib/libpng
*
* Author(s): David "BAILOPAN" Anderson
* ============================
*/

#include <oslink.h>
#include "mapconf_mm.h"
#include <stdio.h>
#include <string>

using namespace std;

MapconfPlugin g_MapconfPlugin;

PLUGIN_EXPOSE(MapconfPlugin, g_MapconfPlugin);


// VALVe ist einfach so *ARGH*
#undef INTERFACEVERSION_SERVERGAMEDLL
#define INTERFACEVERSION_SERVERGAMEDLL "ServerGameDLL004"

#define FStrEq(sz1, sz2) (strcmp((sz1), (sz2)) == 0)
#define FStrEqi(sz1, sz2) (stricmp((sz1), (sz2)) == 0)

//This has all of the necessary hook declarations.  Read it!
#include "meta_hooks.h"

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

void ServerActivate_handler(edict_t *pEdictList, int edictCount, int clientMax)
{
	RETURN_META(MRES_IGNORED);
}

/***********************************************
**         CORE PLUGIN FUNCTIONALITY          **
***********************************************/

#define WRITE( thistext ) strcpy( text, thistext );\
	fwrite( &text, sizeof( char ), strlen(text), conffile )

void strPrune( char* s, int len ){
	for( int i = 0; i < len; i++ )
		s[i] = 0;
	}

void ccmdMapconfListener(){
	char filename[120];
	snprintf( filename, 119, "%s/cfg/mapconfig.ini", g_MapconfPlugin.getGameDir() );
	
	META_CONPRINTF( "[MCFG] Reading config file from:\n[MCFG] \"%s\"\n", filename );
	FILE* conffile = fopen( filename, "r" );
	
	if( conffile == NULL ){
		META_CONPRINT( "[MCFG] File doesn't exist, creating it\n" );
		conffile = fopen( filename, "w" );
		if( !conffile ){
			META_CONPRINT( "[MCFG] Unable to create file.\n" );
			return;
			}
		// The function fwrite() writes nmemb elements of data,
		// each size bytes  long,  to  the  stream  pointed  to  by
		// stream, obtaining them from the location given by ptr.
		char text[50];
		WRITE( "// Default config file for MapConf\n" );
		WRITE( "// http://mapconf.extreme-gaming-clan.de\n" );
		WRITE( "// \n" );
		WRITE( "// This is the map configuration file. Add Cmds for specific maps here.\n" );
		WRITE( "// Format:\n" );
		WRITE( "//   Map sections are named with '[map]' or '[map'. If the closing bracket is not set,\n" );
		WRITE( "//      this means that not the full name was given - example: '[fy_ice' means that these\n" );
		WRITE( "//      are executed for fy_iceworld, fy_iceworld2k_ fy_icewhatever as well.\n" );
		WRITE( "//      Meanwhile, if you specify '[fy_ice]', those commands will only be executed on\n" );
		WRITE( "//      fy_ice, but NOT on fy_iceworld.\n" );
		WRITE( "//   Server and Client Sections are named #server, #client or #all.\n" );
		WRITE( "//      This specifies where the commands are being executed.\n" );
		WRITE( "//   Comments (like these (-.-) ) HAVE to be made with // at the BEGINNING of the line.\n" );
		fclose( conffile );
		return;
		}
	
	// The  function  fread()  reads  nmemb  elements  of  data,
	// each size bytes long, from the stream pointed to by
	// stream, storing them at the location given by ptr.
	char text[5000];
	strPrune( text, 5000 );
	
	int linepos = 0, zeilennr = 0, execmode = 0, wildcard = 0;
	bool ignorelisten = true;
	char zeile[256];
	strPrune( zeile, 256 );
	
	//const char* mapname = g_MapconfPlugin.getMapName();
	const char* mapname = g_SMAPI -> pGlobals() -> mapname.ToCStr();
	
	META_CONPRINTF( "[MCFG] Currently running map: \"%s\"\n", mapname );
	char cmdMap[50];
	
	int freadReturn;
	do{
		freadReturn = fread( text, sizeof( char ), 4998, conffile );
		text[4999] = 0;
		int len = strlen( text );
		
		for( int i = 0; i < len; i++ ){
			if( text[i] != '\n' && linepos < 255 )
				zeile[ linepos++ ] = text[i];
			else{
				//META_CONPRINTF( "Zeile: %s\n", zeile );
				
				int txtlen = strlen( zeile );
				// ANFANG PARSER
				
				char cmd[256];
				strcpy( cmd, zeile );
				
				strPrune( zeile, 256 );
				linepos = 0;
				zeilennr++;
				
				// Check the given cmd for the line beginning...
				if( cmd[0] == cmd[1] == '/' || txtlen == 0 ){
					// skip comment line or whitespace
					continue;
					}
				else if( cmd[0] == '[' ){
					// this is a map name. if terminated with ], mapname has to be fully equal.
					if( cmd[txtlen - 1] == ']' ){
						wildcard = 0;
						// Copy cmd without the [ to mapname UNTIL ] is found
						strPrune( cmdMap, 50 );
						strncpy( cmdMap, (cmd + 1), txtlen - 2 );
						META_CONPRINTF("[MCFG] Found closed map name \"%s\" on line %d\n", cmdMap, zeilennr );
						}
					else{
						// Wildcard was found - check how long the mapname is and save the whole shit...
						wildcard = txtlen - 1; // Whole text except the [
						strPrune( cmdMap, 50 );
						strncpy( cmdMap, (cmd + 1), 49 );
						META_CONPRINTF("[MCFG] Found open map name \"%s\" on line %d\n", cmdMap, zeilennr );
						}
					// Default exec mode: server
					execmode = 2;
					}
				// Server / client / all modifiers
				else if(FStrEq(cmd, "#all"))			execmode = 1;
				else if(FStrEq(cmd, "#server")) 		execmode = 2;
				else if(FStrEq(cmd, "#client")) 		execmode = 3;
				else if(FStrEq(cmd, "#ignorelisten on"))	ignorelisten = true;
				else if(FStrEq(cmd, "#ignorelisten off"))	ignorelisten = false;
				else{
					// Normal Command was found - check if map is running and then exec it
					if( wildcard && strncmp( cmdMap, mapname, wildcard ) != 0 )
						continue;
					if( !wildcard && !FStrEq( cmdMap, mapname ) )
						continue;
					// OK, map is running
					
					META_CONPRINTF( "[MCFG] Found map command \"%s\" on line %d\n", cmd, zeilennr); 
					
					char formCmd[258];
					snprintf( formCmd, 257, "%s\n", cmd );
					
					// Check execmode. For all modes < 3 the command is exec'ed serverside.
					if( execmode < 3 )
						g_MapconfPlugin.sendServerCommand( formCmd );
					
					// For all modes != 2 the command is exec'ed clientside.
					if( execmode != 2 )
						g_MapconfPlugin.sendClientCommand( formCmd, ignorelisten );
					}
				
				// ENDE PARSER
				
				}
			}
		strPrune( text, 5000 );
		}
		while( freadReturn != EOF );
	fclose( conffile );
	}

ConCommand cmd_UserMsgs( "mapconfig", ccmdMapconfListener, "Executes map specific commands" );

char* MapconfPlugin::getGameDir(){
	char* gamedir = new char[100];
	m_Engine -> GetGameDir( gamedir, 99 );
	return gamedir;
	}

void MapconfPlugin::sendServerCommand( const char* command ){
	if( m_Engine == NULL ){
		META_CONPRINTF( "[MCFG] Can't send server command \"%s\"\n", command );
		return;
		}
	m_Engine -> ServerCommand( command );
	}

void MapconfPlugin::sendClientCommand( const char* command, bool ignoreListen = false ){
	if( m_Engine == NULL ){
		META_CONPRINTF( "[MCFG] Can't send client command \"%s\"\n", command );
		return;
		}
	int i = ( ignoreListen ? 2 : 1 );
	for( ; i <= m_plnum; i++ ){
		edict_t* player = m_Engine -> PEntityOfEntIndex(i);
		if( !player || player->IsFree() || !player->GetUnknown() || !player->GetUnknown()->GetBaseEntity() )
			continue;
		m_Engine -> ClientCommand( player, command );
		}
	}

void MapconfPlugin::ServerActivate(edict_t *pEdictList, int edictCount, int clientMax){
	m_plnum = clientMax;
	RETURN_META( MRES_IGNORED );
	}

bool MapconfPlugin::Load(PluginId id, ISmmAPI *ismm, char *error, size_t maxlen, bool late)
{
	PLUGIN_SAVEVARS();

	char iface_buffer[255];
	int num;

	strcpy(iface_buffer, INTERFACEVERSION_SERVERGAMEDLL);
	FIND_IFACE(serverFactory, m_ServerDll, num, iface_buffer, IServerGameDLL *)
	strcpy(iface_buffer, INTERFACEVERSION_VENGINESERVER);
	FIND_IFACE(engineFactory, m_Engine, num, iface_buffer, IVEngineServer *)

	SH_ADD_HOOK_STATICFUNC(IServerGameDLL, ServerActivate, m_ServerDll, ServerActivate_handler, true);
	//Hook ServerActivate to our function
	SH_ADD_HOOK_MEMFUNC(IServerGameDLL, ServerActivate, m_ServerDll, &g_MapconfPlugin, &MapconfPlugin::ServerActivate, true);

	return true;
}

bool MapconfPlugin::Unload(char *error, size_t maxlen)
{
	SH_REMOVE_HOOK_STATICFUNC(IServerGameDLL, ServerActivate, m_ServerDll, ServerActivate_handler, true);
	SH_REMOVE_HOOK_MEMFUNC(IServerGameDLL, ServerActivate, m_ServerDll, &g_MapconfPlugin, &MapconfPlugin::ServerActivate, true);

	return true;
}

bool MapconfPlugin::Pause(char *error, size_t maxlen)
{
	return true;
}

bool MapconfPlugin::Unpause(char *error, size_t maxlen)
{
	return true;
}

void MapconfPlugin::AllPluginsLoaded()
{
}

const char *MapconfPlugin::GetAuthor()
{
	return "MistaGee";
}

const char *MapconfPlugin::GetName()
{
	return "Mapconf Plugin";
}

const char *MapconfPlugin::GetDescription()
{
	return "Runs commnds on specific maps. Port of my MapCommands plugin for AMXX.";
}

const char *MapconfPlugin::GetURL()
{
	return "http://mapconf.extreme-gaming-clan.de/";
}

const char *MapconfPlugin::GetLicense()
{
	return "zlib/libpng";
}

const char *MapconfPlugin::GetVersion()
{
	return "1.00";
}

const char *MapconfPlugin::GetDate()
{
	return __DATE__;
}

const char *MapconfPlugin::GetLogTag()
{
	return "Mapconf";
}

