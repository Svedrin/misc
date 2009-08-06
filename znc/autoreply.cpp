/*
 * Copyright (C) 2008 Michael "Svedrin" Ziegler
 * Contact: diese-addy@funzt-halt.net
 *
 * This is my original autoreply module as I donated it to the ZNC project.
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License version 2 or later as
 * published by the Free Software Foundation.
 */

#include "User.h"
#include <time.h>
#include <map>

#define DEFAULT_MESSAGE "You are talking to ZNC and my master is offline. Please leave a message, I will deliver it as soon as possible."
#define WAIT_TIME_SECONDS 600

class CAutoReply : public CModule {
	public:
		MODCONSTRUCTOR(CAutoReply){
			}
		
		virtual bool OnLoad( const CString& sArgs, CString& sMessage ){
			// We were loaded, so init the reply message.
			if( sArgs.empty() )
				m_sReply = GetNV( "Reply" );
			else
				m_sReply = sArgs;
			
			if( m_sReply.empty() )
				m_sReply = CString( DEFAULT_MESSAGE );
			
			return true;
			}
		
		virtual EModRet OnPrivMsg( CNick& Nick, CString& sMessage ){
			// We received a private message
			if( !m_pUser->IsUserAttached() && !m_sReply.empty() ){
				// No user online, so we need to reply
				long now = (long)time(NULL);
				CString sNick = Nick.GetNick();
				
				// Only reply if we don't know the sender or their last message is older than five minutes
				if( m_mKnownPeers.count( sNick ) == 0 || now - m_mKnownPeers[sNick] > WAIT_TIME_SECONDS ){
					PutIRC( "PRIVMSG " + sNick + " :" + m_sReply );
					}
				m_mKnownPeers[sNick] = now;
				}
			
			return CONTINUE;
			}
		
		virtual EModRet OnPrivNotice( CNick& Nick, CString& sMessage ){
			// Here come the hax
			return OnPrivMsg( Nick, sMessage );
			}
		
		virtual void OnModCommand( const CString& sCommand ){
			// A few user commands
			CString sCmdName = sCommand.Token(0).AsLower();
			
			if( sCmdName == "set" ){
				CString sReply = sCommand.Token(1, true);
				m_sReply = sReply;
				SetNV( "Reply", m_sReply );
				PutModule("Reply message set to:");
				PutModule( m_sReply );
				}
			
			else if( sCmdName == "show" ){
				if( m_sReply.empty() )
					PutModule( "No reply message set" );
				else{
					PutModule( "Current message: " );
					PutModule( m_sReply );
					}
				}
			
			else{
				PutModule( "Commands: set <message>, show" );
				}
			}
	
	private:
		CString m_sReply;
		map<CString, long> m_mKnownPeers;
	};

MODULEDEFS( CAutoReply, "Automatic reply to /query when all users offline" )
