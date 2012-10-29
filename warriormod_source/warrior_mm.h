/* ======== sample_mm ========
* Copyright (C) 2004-2005 Metamod:Source Development Team
* No warranties of any kind
*
* License: zlib/libpng
*
* Author(s): David "BAILOPAN" Anderson
* ============================
*/

#ifndef _INCLUDE_WarriorPlugin_H
#define _INCLUDE_WarriorPlugin_H

#include <ISmmPlugin.h>
#include <sourcehook/sourcehook.h>
#include <igameevents.h>
#include <filesystem.h>

#include <dlls/iplayerinfo.h>

#include "eventManager.h"

#define WARRIOR_VERSION "1.6.4"

class WarriorPlugin : public ISmmPlugin, public IMetamodListener
{
public:
	bool Load(PluginId id, ISmmAPI *ismm, char *error, size_t maxlen, bool late);
	bool Unload(char *error, size_t maxlen);
	void AllPluginsLoaded();
	bool Pause(char *error, size_t maxlen)
	{
		return true;
	}
	bool Unpause(char *error, size_t maxlen)
	{
		return true;
	}
	
public:
	int GetApiVersion() { return PLAPI_VERSION; }
public:
	IVEngineServer* getEngine(){
		return m_Engine;
		}
	
	IServerPluginHelpers* getServerPluginHelpers(){
		return m_ServerPluginHelpers;
		}
	
	IPlayerInfoManager* getPlayerInfoManager(){
		return m_PlayerInfoManager;
		}
	
	IServerGameEnts* getServerEnts(){
		return m_ServerEnts;
		}
	
	int getMaxPlayers(){
		return m_MaxPlayers;
		}
	
	const char *GetAuthor()
	{
		return "MistaGee";
	}
	const char *GetName()
	{
#ifdef _DeBuG
		return "WarriorMod (Debug)";
#else
		return "WarriorMod";
#endif
	}
	const char *GetDescription()
	{
		return "Clanwar manager";
	}
	const char *GetURL()
	{
		return "http://warriormod.extreme-gaming-clan.de/";
	}
	const char *GetLicense()
	{
		return "zlib/libpng";
	}
	const char *GetVersion()
	{
		return WARRIOR_VERSION;
	}
	const char *GetDate()
	{
		return __DATE__;
	}
	const char *GetLogTag()
	{
		return "WAR";
	}
public:
	//These functions are from IServerPluginCallbacks
	//Note, the parameters might be a little different to match the actual calls!

	//Called on ServerActivate.  Same definition as server plugins
	void ServerActivate(edict_t *pEdictList, int edictCount, int clientMax);

	//Called when a client uses a command.  Unlike server plugins, it's void.
	// You can still supercede the gamedll through RETURN_META(MRES_SUPERCEDE).
#ifdef SourceHookMitRueckgabewert
	bool ClientCommand(edict_t *pEntity);
#else
	void ClientCommand(edict_t *pEntity);
#endif

private:
	IGameEventManager2 *m_GameEventManager;	
	IVEngineServer *m_Engine;
	IServerGameDLL *m_ServerDll;
	IServerGameEnts *m_ServerEnts;
	IServerGameClients *m_ServerClients;
	IBaseFileSystem *m_BaseFileSystem;
	IServerPluginHelpers *m_ServerPluginHelpers;
	IPlayerInfoManager *m_PlayerInfoManager;
	SourceHook::CallClass<IVEngineServer> *m_Engine_CC;
	int m_MaxPlayers;
};

class MyListener : public IMetamodListener
{
public:
	virtual void *OnMetamodQuery(const char *iface, int *ret);
};

extern WarriorPlugin	g_WarriorPlugin;
extern GeeventManager	g_eventManager;
PLUGIN_GLOBALVARS();

bool FireEvent_Handler(IGameEvent *event, bool bDontBroadcast);

#endif //_INCLUDE_WarriorPlugin_H
