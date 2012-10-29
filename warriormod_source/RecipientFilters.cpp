/* ======== SourceMod ========
* Copyright (C) 2004-2005 SourceMod Development Team
* No warranties of any kind
*
* File: RecipientFilters.cpp
*     Contains useful Recipient Filters (source code)
*
* License: See LICENSE.txt
*
* Author(s): PM, Damaged Soul
* Contributors: MistaGee
* ============================
*/

#include "RecipientFilters.h"

// =============== CRFGeneral Implementation ===============
CRFGeneral::CRFGeneral(bool reliable, bool initmsg) : m_Reliable(reliable), m_InitMessage(initmsg)
{
	m_Engine = g_eventManager.getEngineServer();
	m_Recipients.clear();
}

bool CRFGeneral::IsReliable() const
{
	return m_Reliable;
}

bool CRFGeneral::IsInitMessage() const
{
	return m_InitMessage;
}

int CRFGeneral::GetRecipientCount() const
{
	return (int)m_Recipients.size();
}

int CRFGeneral::GetRecipientIndex(int slot) const
{
	return m_Recipients[slot];
}
	
void CRFGeneral::AddPlayer(int id)
{
	if ( id > 0 && id <= g_eventManager.getMaxPlayers()
		&& std::find(m_Recipients.begin(), m_Recipients.end(), id) == m_Recipients.end()) // Wenn noch nicht drin,
		m_Recipients.push_back(id); // einfuegen
}

void CRFGeneral::AddPlayer(edict_t *ed)
{
	AddPlayer( m_Engine -> IndexOfEdict(ed) );
}

void CRFGeneral::AddAllPlayers()
{
	m_Recipients.clear();
	IPlayerInfoManager* plIM = g_eventManager.getPlayerInfoManager();
	
	for (int i = 1; i <= g_eventManager.getMaxPlayers(); i++)
	{
		edict_t *player = m_Engine -> PEntityOfEntIndex( i );
		if (!player || player->IsFree() || !player->GetUnknown() || !player->GetUnknown()->GetBaseEntity() ||
				plIM -> GetPlayerInfo( player ) -> GetTeamIndex() < 2 ) // NO specs and joining guys
			continue;
		AddPlayer( i );
	}
}

void CRFGeneral::RemovePlayer(int id)
{
	std::remove(m_Recipients.begin(), m_Recipients.end(), id);
}

void CRFGeneral::RemovePlayer(edict_t *ed)
{
	RemovePlayer(g_WarriorPlugin.getEngine()->IndexOfEdict(ed));
}

void CRFGeneral::RemoveAllPlayers()
{
	m_Recipients.clear();
}

// =============== CRFBroadcast Implementation ===============
CRFBroadcast::CRFBroadcast(bool reliable, bool initmsg) : CRFGeneral(reliable, initmsg)
{
	AddAllPlayers();
}

// =============== CRFSingle Implementation ===============
CRFSingle::CRFSingle(int id, bool reliable, bool initmsg) : CRFGeneral(reliable, initmsg)
{
	AddPlayer(id);
}
