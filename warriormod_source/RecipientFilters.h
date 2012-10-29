#ifndef _RECIPIENTFILTERS_H_
#define _RECIPIENTFILTERS_H_
/* ======== SourceMod ========
* Copyright (C) 2004-2005 SourceMod Development Team
* No warranties of any kind
*
* File: RecipientFilters.h
*     Contains useful Recipient Filters (header)
*
* License: See LICENSE.txt
*
* Author(s): PM, Damaged Soul
* Contributors: MistaGee
* ============================
*/

#include <vector>
#include <algorithm>		// find
#include <irecipientfilter.h>
#include "warrior_mm.h"

class CRFGeneral : public IRecipientFilter
{
	bool m_Reliable;
	bool m_InitMessage;

	std::vector<int> m_Recipients;
	IVEngineServer *m_Engine;
public:
	CRFGeneral(bool reliable = true, bool initmsg = false);

	bool IsReliable() const;
	bool IsInitMessage() const;

	int GetRecipientCount() const;
	int GetRecipientIndex(int slot) const;

	void AddPlayer(int id);
	void AddPlayer(edict_t *ed);
	void AddAllPlayers();

	void RemovePlayer(int id);
	void RemovePlayer(edict_t *ed);
	void RemoveAllPlayers();
};

class CRFBroadcast : public CRFGeneral
{
public:
	CRFBroadcast(bool reliable = true, bool initmsg = false);
};

class CRFSingle : public CRFGeneral
{
public:
	CRFSingle(/*IVHalfLife *pHL2,*/ int id, bool reliable = true, bool initmsg = false);
};
#endif
