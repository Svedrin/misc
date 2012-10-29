#ifndef _EVENTMANAGER_H_
#define _EVENTMANAGER_H_

#define EVM_SETCVAR( convar ) g_eventManager.setCVar##convar ( &cvar_##convar )

#define EVM_CVAR_FUNCTIONS( convar ) ConVar* getCVar##convar (){ return cvar_##convar ; };\
		void setCVar##convar ( ConVar* v_cvar_##convar ){\
			cvar_##convar = v_cvar_##convar ;\
			}

#define EVM_REGCVAR( convar ) ConVar* cvar_##convar ;

#define WITH_MYSQL

#ifdef WITH_MYSQL
#include <mysql/mysql.h>
#endif

class CRFGeneral;

class GeeventManager {
	public:
		GeeventManager();
		~GeeventManager();
		META_RES		clientCommand	( edict_t* uEntity, const char* command, const char* args );
		void			playerDisconnect( int uID, const char* reason );
		void			playerSpawn	( );
		void			playerTeam	( int uID, int newTeam, int oldTeam = 0 );
		void			roundEnd	( int winner );
		void			roundFreezeEnd	( );
		void			roundStart	( );
		void			serverActivate	( int clientMax = 32 );
		void			weaponFire	( int uID, const char* uWeapon );
		
		void			goLive		( );
		void			goKnife 	( );
		void			rdy4Live	( bool overrideCvar = false );
		void			rdy4Knife	( );
		
		void			kickbanTeam	( int team, int time );
		
		// Function to init mysql
		void			OneTimeInit();
		// Function resetting the clanwar
		void			init_vars();
		
		// These create functions allowing to set and get the CVar pointers
		// See the above macros for further information
		EVM_CVAR_FUNCTIONS( AskReady )
		EVM_CVAR_FUNCTIONS( RoundCount)
		EVM_CVAR_FUNCTIONS( FadeToBlack )
		EVM_CVAR_FUNCTIONS( Pausable )
		EVM_CVAR_FUNCTIONS( Record )
		EVM_CVAR_FUNCTIONS( ChPassword )
		EVM_CVAR_FUNCTIONS( mysql_host )
		EVM_CVAR_FUNCTIONS( mysql_user )
		EVM_CVAR_FUNCTIONS( mysql_pass )
		EVM_CVAR_FUNCTIONS( mysql_db )
		EVM_CVAR_FUNCTIONS( mysql_table )
		EVM_CVAR_FUNCTIONS( mysql_enable )
		
		int			getMaxPlayers()		{ return m_MaxPlayers;		};
		ISmmAPI* 		getSMApi()		{ return m_SMAPI;		};
		IVEngineServer* 	getEngineServer()	{ return m_Engine;		};
		IPlayerInfoManager*	getPlayerInfoManager()	{ return m_PlayerInfoManager;	};
		IServerGameDLL* 	getServerGameDLL()	{ return m_ServerDll;		};
		IBaseFileSystem* 	getBaseFileSystem()	{ return m_BaseFileSystem;	};
		
		void setSMApi( ISmmAPI* v_SMAPI){
			m_SMAPI = v_SMAPI;
			}
		void setEngineServer( IVEngineServer* v_Engine ){
			m_Engine = v_Engine;
			}
		void setServerGameDLL( IServerGameDLL* v_ServerDll ){
			m_ServerDll = v_ServerDll;
			}
		void setPlayerInfoManager( IPlayerInfoManager* v_PlayerInfoManager ){
			m_PlayerInfoManager = v_PlayerInfoManager;
			}
		void setBaseFileSystem( IBaseFileSystem* v_BaseFileSystem ){
			m_BaseFileSystem = v_BaseFileSystem;
			}
		
#ifdef _DeBuG
		// Functions to print debug info
		void			list_players();
		void			list_debug_info();
		// allows functions to be called from outside the class in Debug compiles
		void			findTeamNames();
		void 			findPlayerInfo();
#endif
		
	private:
		float			m_LastSpawn;
		int			m_TeamScores[2];
		int			m_TeamScoresAtTeamChange[2];
		char			m_TeamNames[2][256];
		char			m_DesiredTeamNames[2][256];
		int			m_TeamNameSetByUser[2];
		int			m_RestartsRemaining;
		int			m_AfterRestartsDo;
		int			m_RoundsPlayed;
		int			m_Rounds2Play;
		bool			m_TeamsHaveBeenChanged;
		bool			m_WaitingForReady_T;
		bool			m_WaitingForReady_CT;
		bool			m_KnifeRound;
		bool			m_Live;
		bool			m_OverrideCvar;
		int			m_TeamToSayStayLeave;
		int			m_TeamChangesRemaining;
		bool			m_ConfigHasBeenDone;
		int			m_MaxPlayers;
		IPlayerInfo*		m_playerInfo[32];
		bool			m_SaidMajorityThingy;
		const char*		m_newPass;
		int			m_LastKnifeRoundWinner;
		int			m_TimeStamp;
		ISmmAPI*		m_SMAPI;
		IServerGameDLL*		m_ServerDll;
		IVEngineServer* 	m_Engine;
		IPlayerInfoManager*	m_PlayerInfoManager;
		IBaseFileSystem*	m_BaseFileSystem;
		KeyValues*		m_ConfigFile;
#ifdef WITH_MYSQL
		MYSQL*			m_mysql;
#endif
		
		// These create member variables for the CVar pointers
		// See the above macros for further information
		EVM_REGCVAR( AskReady )
		EVM_REGCVAR( RoundCount )
		EVM_REGCVAR( FadeToBlack )
		EVM_REGCVAR( Pausable )
		EVM_REGCVAR( Record )
		EVM_REGCVAR( ChPassword )
		EVM_REGCVAR( mysql_host )
		EVM_REGCVAR( mysql_user )
		EVM_REGCVAR( mysql_pass )
		EVM_REGCVAR( mysql_db )
		EVM_REGCVAR( mysql_table )
		EVM_REGCVAR( mysql_enable )
		
		void			do_config();
		void			displayGetReadyMsg();
		void			forceTeamChange();
		bool			checkTeamSizes();
		
#ifndef _DeBuG
		// Normally, these are helper functions that only this certain class needs.
		void			findTeamNames();
		void 			findPlayerInfo();
#endif
		int*			findTeamMemberCount();
		int			findPlayerCount ( bool CountSpectators = false );
		int			findPlayerIndex ( int  uid );
		const char*		findPlayerName  ( int  uid );
		edict_t*		findPlayerEnt   ( int  uid );
		int			findPlayerTeam  ( int  uid );
		
		void			ClassicMenu( edict_t* pEntity, int allowedkeys, int time, const char *menubody );
		void			ClassicMenu( int id,           int allowedkeys, int time, const char *menubody );
		void			ClassicMenu( CRFGeneral* rf,   int allowedkeys, int time, const char *menubody );
		
		int			UserMessageIndex( const char *messageName );
		CRFGeneral*		MakeRfAllPlayers();
		
		void			strPrune( char* s, int len);
		void			strPruneInvalidChars( char* string, int len );
		char*			findLongestMatch( const char* s1, const char* s2 );
		void			trim( char* string );
		const char*		getRandomString( const int len );
	};

#endif // defined _EVENTMANAGER_H_
