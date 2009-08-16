/* ======== Mapconf_mm ========
* Copyright (C) 2004-2005 Metamod:Source Development Team
* No warranties of any kind
*
* License: zlib/libpng
*
* Author(s): David "BAILOPAN" Anderson
* ============================
*/

#ifndef _INCLUDE_SAMPLEPLUGIN_H
#define _INCLUDE_SAMPLEPLUGIN_H

#include <ISmmPlugin.h>

class MapconfPlugin : public ISmmPlugin
{
public:
	bool Load(PluginId id, ISmmAPI *ismm, char *error, size_t maxlen, bool late);
	bool Unload(char *error, size_t maxlen);
	bool Pause(char *error, size_t maxlen);
	bool Unpause(char *error, size_t maxlen);
	void AllPluginsLoaded();
	
	//Called on ServerActivate.  Same definition as server plugins
	void ServerActivate(edict_t *pEdictList, int edictCount, int clientMax);

	void sendServerCommand( const char* command );
	void sendClientCommand( const char* command, bool ignoreListen = false );
	char* getGameDir();
public:
	const char *GetAuthor();
	const char *GetName();
	const char *GetDescription();
	const char *GetURL();
	const char *GetLicense();
	const char *GetVersion();
	const char *GetDate();
	const char *GetLogTag();
private:
	int m_plnum;
	IVEngineServer *m_Engine;
	IServerGameDLL *m_ServerDll;
	IServerGameDLL *m_ServerDll_CC;
};

extern MapconfPlugin g_MapconfPlugin;

PLUGIN_GLOBALVARS();

//Called on ServerActivate.  Same definition as server plugins
void ServerActivate_handler(edict_t *pEdictList, int edictCount, int clientMax);

#endif //_INCLUDE_SAMPLEPLUGIN_H
