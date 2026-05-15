import express from 'express';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { initDb, queryAll, queryOne, run } from './db/index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());
app.use(express.static(join(__dirname, '../public')));

// ============ TAG ROUTES ============

// Get all tags
app.get('/api/tags', (req, res) => {
  try {
    const tags = queryAll('SELECT * FROM tags ORDER BY sort_order, name');
    res.json(tags);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Create tag
app.post('/api/tags', (req, res) => {
  const { name, color } = req.body;
  if (!name) {
    return res.status(400).json({ error: 'Name is required' });
  }
  try {
    const maxOrder = queryOne('SELECT MAX(sort_order) as max FROM tags');
    const sortOrder = (maxOrder?.max || 0) + 1;
    const result = run(
      'INSERT INTO tags (name, color, sort_order) VALUES (?, ?, ?)',
      [name, color || '#6b7280', sortOrder]
    );
    const tag = queryOne('SELECT * FROM tags WHERE id = ?', [result.lastInsertRowid]);
    res.status(201).json(tag);
  } catch (err) {
    if (err.message.includes('UNIQUE constraint')) {
      return res.status(400).json({ error: 'Tag name already exists' });
    }
    res.status(500).json({ error: err.message });
  }
});

// Update tag
app.put('/api/tags/:id', (req, res) => {
  const { id } = req.params;
  const { name, color, sort_order } = req.body;
  try {
    const existing = queryOne('SELECT * FROM tags WHERE id = ?', [id]);
    if (!existing) {
      return res.status(404).json({ error: 'Tag not found' });
    }
    run(
      'UPDATE tags SET name = ?, color = ?, sort_order = ? WHERE id = ?',
      [
        name || existing.name,
        color || existing.color,
        sort_order !== undefined ? sort_order : existing.sort_order,
        id
      ]
    );
    const tag = queryOne('SELECT * FROM tags WHERE id = ?', [id]);
    res.json(tag);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Delete tag
app.delete('/api/tags/:id', (req, res) => {
  const { id } = req.params;
  try {
    const result = run('DELETE FROM tags WHERE id = ?', [id]);
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Tag not found' });
    }
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ============ EVENT ROUTES ============

// Get events (with optional date range filter)
app.get('/api/events', (req, res) => {
  const { start, end, tag_id } = req.query;
  try {
    let query = `
      SELECT e.*, t.name as tag_name, t.color as tag_color 
      FROM events e 
      LEFT JOIN tags t ON e.tag_id = t.id
      WHERE 1=1
    `;
    const params = [];
    
    if (start) {
      query += ' AND e.end_date >= ?';
      params.push(start);
    }
    if (end) {
      query += ' AND e.start_date <= ?';
      params.push(end);
    }
    if (tag_id) {
      query += ' AND e.tag_id = ?';
      params.push(tag_id);
    }
    
    query += ' ORDER BY e.start_date, e.title';
    
    const events = queryAll(query, params);
    res.json(events);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get single event
app.get('/api/events/:id', (req, res) => {
  const { id } = req.params;
  try {
    const event = queryOne(`
      SELECT e.*, t.name as tag_name, t.color as tag_color 
      FROM events e 
      LEFT JOIN tags t ON e.tag_id = t.id
      WHERE e.id = ?
    `, [id]);
    if (!event) {
      return res.status(404).json({ error: 'Event not found' });
    }
    res.json(event);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Create event
app.post('/api/events', (req, res) => {
  const { title, start_date, end_date, tag_id, is_travel, is_preliminary, description } = req.body;
  
  if (!title || !start_date || !end_date) {
    return res.status(400).json({ error: 'Title, start_date, and end_date are required' });
  }
  
  if (start_date > end_date) {
    return res.status(400).json({ error: 'Start date must be before or equal to end date' });
  }
  
  try {
    const result = run(`
      INSERT INTO events (title, start_date, end_date, tag_id, is_travel, is_preliminary, description)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `, [
      title,
      start_date,
      end_date,
      tag_id || null,
      is_travel ? 1 : 0,
      is_preliminary ? 1 : 0,
      description || null
    ]);
    
    const event = queryOne(`
      SELECT e.*, t.name as tag_name, t.color as tag_color 
      FROM events e 
      LEFT JOIN tags t ON e.tag_id = t.id
      WHERE e.id = ?
    `, [result.lastInsertRowid]);
    
    res.status(201).json(event);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Update event
app.put('/api/events/:id', (req, res) => {
  const { id } = req.params;
  const { title, start_date, end_date, tag_id, is_travel, is_preliminary, description } = req.body;
  
  try {
    const existing = queryOne('SELECT * FROM events WHERE id = ?', [id]);
    if (!existing) {
      return res.status(404).json({ error: 'Event not found' });
    }
    
    const newStartDate = start_date || existing.start_date;
    const newEndDate = end_date || existing.end_date;
    
    if (newStartDate > newEndDate) {
      return res.status(400).json({ error: 'Start date must be before or equal to end date' });
    }
    
    run(`
      UPDATE events 
      SET title = ?, start_date = ?, end_date = ?, tag_id = ?, 
          is_travel = ?, is_preliminary = ?, description = ?,
          updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `, [
      title !== undefined ? title : existing.title,
      newStartDate,
      newEndDate,
      tag_id !== undefined ? (tag_id || null) : existing.tag_id,
      is_travel !== undefined ? (is_travel ? 1 : 0) : existing.is_travel,
      is_preliminary !== undefined ? (is_preliminary ? 1 : 0) : existing.is_preliminary,
      description !== undefined ? description : existing.description,
      id
    ]);
    
    const event = queryOne(`
      SELECT e.*, t.name as tag_name, t.color as tag_color 
      FROM events e 
      LEFT JOIN tags t ON e.tag_id = t.id
      WHERE e.id = ?
    `, [id]);
    
    res.json(event);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Delete event
app.delete('/api/events/:id', (req, res) => {
  const { id } = req.params;
  try {
    const result = run('DELETE FROM events WHERE id = ?', [id]);
    if (result.changes === 0) {
      return res.status(404).json({ error: 'Event not found' });
    }
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ============ STATS ROUTE ============

app.get('/api/stats', (req, res) => {
  const { year } = req.query;
  const yearStart = year ? `${year}-01-01` : null;
  const yearEnd = year ? `${year}-12-31` : null;
  
  try {
    let travelQuery = 'SELECT start_date, end_date FROM events WHERE is_travel = 1';
    let tagQuery = `
      SELECT t.id, t.name, t.color, COUNT(e.id) as event_count
      FROM tags t
      LEFT JOIN events e ON t.id = e.tag_id
    `;
    
    const travelParams = [];
    const tagParams = [];
    
    if (yearStart && yearEnd) {
      travelQuery += ' AND end_date >= ? AND start_date <= ?';
      travelParams.push(yearStart, yearEnd);
      tagQuery += ' WHERE (e.id IS NULL OR (e.end_date >= ? AND e.start_date <= ?))';
      tagParams.push(yearStart, yearEnd);
    }
    
    tagQuery += ' GROUP BY t.id ORDER BY t.sort_order';
    
    // Calculate travel days (accounting for overlapping events)
    const travelEvents = queryAll(travelQuery, travelParams);
    const travelDays = new Set();
    
    for (const event of travelEvents) {
      let current = new Date(event.start_date);
      const end = new Date(event.end_date);
      
      // Clamp to year if filtering
      if (yearStart && yearEnd) {
        if (current < new Date(yearStart)) current = new Date(yearStart);
        if (end > new Date(yearEnd)) end.setTime(new Date(yearEnd).getTime());
      }
      
      while (current <= end) {
        travelDays.add(current.toISOString().split('T')[0]);
        current.setDate(current.getDate() + 1);
      }
    }
    
    // Calculate days per tag
    const tagStats = queryAll(tagQuery, tagParams);
    
    // Add total_days to each tag
    for (const tag of tagStats) {
      const tagEventsQuery = yearStart
        ? 'SELECT start_date, end_date FROM events WHERE tag_id = ? AND end_date >= ? AND start_date <= ?'
        : 'SELECT start_date, end_date FROM events WHERE tag_id = ?';
      const tagEventsParams = yearStart ? [tag.id, yearStart, yearEnd] : [tag.id];
      const tagEvents = queryAll(tagEventsQuery, tagEventsParams);
      
      const tagDays = new Set();
      for (const event of tagEvents) {
        let current = new Date(event.start_date);
        const end = new Date(event.end_date);
        
        if (yearStart && yearEnd) {
          if (current < new Date(yearStart)) current = new Date(yearStart);
          if (end > new Date(yearEnd)) end.setTime(new Date(yearEnd).getTime());
        }
        
        while (current <= end) {
          tagDays.add(current.toISOString().split('T')[0]);
          current.setDate(current.getDate() + 1);
        }
      }
      tag.total_days = tagDays.size;
    }
    
    res.json({
      travel_days: travelDays.size,
      tag_stats: tagStats,
      year: year || 'all'
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ============ EXPORT ROUTE ============

app.get('/api/export', (req, res) => {
  const { year } = req.query;
  
  try {
    let query = `
      SELECT e.*, t.name as tag_name
      FROM events e
      LEFT JOIN tags t ON e.tag_id = t.id
    `;
    const params = [];
    
    if (year) {
      query += ' WHERE e.end_date >= ? AND e.start_date <= ?';
      params.push(`${year}-01-01`, `${year}-12-31`);
    }
    
    query += ' ORDER BY e.start_date, e.title';
    
    const events = queryAll(query, params);
    
    let output = year ? `YEARVIEW EXPORT - ${year}\n` : 'YEARVIEW EXPORT - ALL EVENTS\n';
    output += '='.repeat(50) + '\n\n';
    
    for (const event of events) {
      const startDate = new Date(event.start_date).toLocaleDateString('en-US', {
        weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
      });
      const endDate = new Date(event.end_date).toLocaleDateString('en-US', {
        weekday: 'short', year: 'numeric', month: 'short', day: 'numeric'
      });
      
      const dateRange = event.start_date === event.end_date 
        ? startDate 
        : `${startDate} - ${endDate}`;
      
      const tags = [];
      if (event.tag_name) tags.push(event.tag_name);
      if (event.is_travel) tags.push('TRAVEL');
      if (event.is_preliminary) tags.push('TENTATIVE');
      
      output += `${event.title}\n`;
      output += `  ${dateRange}\n`;
      if (tags.length) output += `  [${tags.join(', ')}]\n`;
      if (event.description) output += `  ${event.description}\n`;
      output += '\n';
    }
    
    res.setHeader('Content-Type', 'text/plain');
    res.setHeader('Content-Disposition', `attachment; filename="yearview-${year || 'all'}.txt"`);
    res.send(output);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Serve index.html for all other routes
app.get('*', (req, res) => {
  res.sendFile(join(__dirname, '../public/index.html'));
});

// Initialize database then start server
initDb().then(() => {
  app.listen(PORT, () => {
    console.log(`YearView server running at http://localhost:${PORT}`);
  });
}).catch(err => {
  console.error('Failed to initialize database:', err);
  process.exit(1);
});
