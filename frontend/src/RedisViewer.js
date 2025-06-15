import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Typography,
  Box,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

function RedisViewer() {
  const [contents, setContents] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchContents = async () => {
    try {
      const response = await axios.get(`${API_URL}/redis-contents`);
      setContents(response.data.contents);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchContents();
    // Refresh every 5 seconds
    const interval = setInterval(fetchContents, 5000);
    return () => clearInterval(interval);
  }, []);

  const formatValue = (value) => {
    try {
      // Try to parse as JSON
      const parsed = JSON.parse(value);
      return JSON.stringify(parsed, null, 2);
    } catch {
      // If not JSON, return as is
      return value;
    }
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center' }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Paper elevation={3} sx={{ p: 3 }}>
          <Typography color="error">Error: {error}</Typography>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Redis Contents
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Auto-refreshing every 5 seconds
        </Typography>
      </Paper>

      <List>
        {Object.entries(contents).map(([key, value]) => (
          <React.Fragment key={key}>
            <ListItem>
              <ListItemText
                primary={
                  <Typography variant="subtitle1" component="div" sx={{ fontWeight: 'bold' }}>
                    {key}
                  </Typography>
                }
                secondary={
                  <Paper 
                    variant="outlined" 
                    sx={{ 
                      mt: 1, 
                      p: 2, 
                      backgroundColor: 'grey.50',
                      fontFamily: 'monospace',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word'
                    }}
                  >
                    <Typography
                      component="pre"
                      variant="body2"
                      sx={{
                        margin: 0,
                        fontFamily: 'inherit',
                        fontSize: '0.875rem',
                        lineHeight: 1.5,
                      }}
                    >
                      {formatValue(value)}
                    </Typography>
                  </Paper>
                }
              />
            </ListItem>
            <Divider />
          </React.Fragment>
        ))}
      </List>
    </Container>
  );
}

export default RedisViewer; 