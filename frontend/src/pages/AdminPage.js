import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminService } from '../services/adminService';
import '../styles/AdminPage.css';

const AdminPage = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('users');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // User Management State
  const [users, setUsers] = useState([]);
  const [selectedUsers, setSelectedUsers] = useState([]);
  
  // Course Management State
  const [courses, setCourses] = useState([]);
  const [selectedCourses, setSelectedCourses] = useState([]);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadPath, setUploadPath] = useState('');
  const [uploading, setUploading] = useState(false);
  const [pathSuggestions, setPathSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  
  // System Settings State
  const [healthInfo, setHealthInfo] = useState(null);

  useEffect(() => {
    // Check authentication
    if (!adminService.isAuthenticated()) {
      navigate('/settings');
      return;
    }
    
    // Load initial data based on active tab
    loadTabData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, navigate]);

  const loadTabData = async () => {
    setLoading(true);
    setError(null);
    
    try {

        const usersData = await adminService.getUsers();
        setUsers(usersData);

        const coursesData = await adminService.getCourses();
        setCourses(coursesData.courses || []);

        const health = await adminService.getHealth();
        setHealthInfo(health);
        // console.table((usersData));
        // console.table(coursesData.courses);
        // console.log(health);
    } catch (err) {
      console.error('Error loading tab data:', err);
      setError('Failed to load data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // User Management Functions
  const handleDeleteUsers = async () => {
    if (selectedUsers.length === 0) {
      alert('Please select users to delete');
      return;
    }

    if (!window.confirm(`Are you sure you want to delete ${selectedUsers.length} user(s)? This action cannot be undone.`)) {
      return;
    }

    setLoading(true);
    const errors = [];
    
    for (const email of selectedUsers) {
      try {
        await adminService.deleteUser(email);
      } catch (err) {
        errors.push(email);
      }
    }

    if (errors.length > 0) {
      setError(`Failed to delete: ${errors.join(', ')}`);
    }

    setSelectedUsers([]);
    loadTabData();
  };

  const toggleUserSelection = (email) => {
    setSelectedUsers(prev => 
      prev.includes(email) 
        ? prev.filter(e => e !== email)
        : [...prev, email]
    );
  };

  // Course Management Functions
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    setUploadFile(file);
  };

  const handleUploadCourse = async () => {
    if (!uploadFile) {
      alert('Please select a file to upload');
      return;
    }

    if (!uploadPath.trim()) {
      alert('Please specify a target path');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      await adminService.uploadCourse(uploadFile, uploadPath);
      setUploadFile(null);
      setUploadPath('');
      
      alert('Course uploaded successfully!');
      
      // Ask if user wants to rebuild now
      const shouldRebuild = window.confirm(
        'Would you like to rebuild the vector database now to include the new course?\n\n(You can also do this later from the System Settings tab)'
      );
      
      if (shouldRebuild) {
        // Trigger rebuild without additional confirmation
        try {
          await adminService.triggerRebuild();
          alert('Rebuild started in the background. This may take several minutes.');
        } catch (err) {
          console.error('Error triggering rebuild:', err);
          setError('Upload succeeded but rebuild failed. You can trigger it manually from System Settings.');
        }
      }
      
      loadTabData();
    } catch (err) {
      console.error('Error uploading course:', err);
      setError('Failed to upload course. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteCourses = async () => {
    if (selectedCourses.length === 0) {
      alert('Please select courses to delete');
      return;
    }

    if (!window.confirm(`Are you sure you want to delete ${selectedCourses.length} course(s)? This action cannot be undone.`)) {
      return;
    }

    setLoading(true);
    
    try {
      const result = await adminService.deleteCourses(selectedCourses);
      
      if (result.errors && result.errors.length > 0) {
        setError(`Some items failed to delete: ${result.errors.join(', ')}`);
      } else {
        alert('Courses deleted successfully!');
        
        // Ask if user wants to rebuild now
        const shouldRebuild = window.confirm(
          'Would you like to rebuild the vector database now to update the index?\n\n(You can also do this later from the System Settings tab)'
        );
        
        if (shouldRebuild) {
          try {
            await adminService.triggerRebuild();
            alert('Rebuild started in the background. This may take several minutes.');
          } catch (err) {
            console.error('Error triggering rebuild:', err);
            setError('Delete succeeded but rebuild failed. You can trigger it manually from System Settings.');
          }
        }
      }
      
      setSelectedCourses([]);
      loadTabData();
    } catch (err) {
      console.error('Error deleting courses:', err);
      setError('Failed to delete courses. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const toggleCourseSelection = (path, node = null) => {
    // If we have a node and it's a directory, get all child paths
    const getAllPaths = (n) => {
      let paths = [n.path];
      if (n.children) {
        n.children.forEach(child => {
          paths = paths.concat(getAllPaths(child));
        });
      }
      return paths;
    };

    // Find the node in courses tree if not provided
    const findNode = (nodes, targetPath) => {
      for (const n of nodes) {
        if (n.path === targetPath) return n;
        if (n.children) {
          const found = findNode(n.children, targetPath);
          if (found) return found;
        }
      }
      return null;
    };

    const targetNode = node || findNode(courses, path);
    
    if (targetNode && targetNode.type === 'directory' && targetNode.children) {
      // Get all paths including children
      const allPaths = getAllPaths(targetNode);
      const isCurrentlySelected = selectedCourses.includes(path);
      
      setSelectedCourses(prev => {
        if (isCurrentlySelected) {
          // Deselect all
          return prev.filter(p => !allPaths.includes(p));
        } else {
          // Select all
          return [...new Set([...prev, ...allPaths])];
        }
      });
    } else {
      // Single file toggle
      setSelectedCourses(prev => 
        prev.includes(path) 
          ? prev.filter(p => p !== path)
          : [...prev, path]
      );
    }
  };

  // Get all folder paths for autocomplete suggestions
  const getAllFolderPaths = (nodes, prefix = '') => {
    let paths = [];
    for (const node of nodes) {
      if (node.type === 'directory') {
        paths.push(node.path);
        if (node.children) {
          paths = paths.concat(getAllFolderPaths(node.children, node.path + '/'));
        }
      }
    }
    return paths;
  };

  // Filter suggestions based on input
  const getFilteredSuggestions = (input) => {
    if (!input) {
      // Show top-level folders when input is empty
      return courses.filter(c => c.type === 'directory').map(c => c.path);
    }
    const allPaths = getAllFolderPaths(courses);
    const inputLower = input.toLowerCase();
    return allPaths.filter(p => p.toLowerCase().includes(inputLower) || p.toLowerCase().startsWith(inputLower));
  };

  // Handle path input change with suggestions
  const handlePathInputChange = (e) => {
    const value = e.target.value;
    setUploadPath(value);
    const suggestions = getFilteredSuggestions(value);
    setPathSuggestions(suggestions);
    setShowSuggestions(suggestions.length > 0);
  };

  // Handle suggestion click
  const handleSuggestionClick = (suggestion) => {
    setUploadPath(suggestion + '/');
    setShowSuggestions(false);
  };

  // System Settings Functions
  const handleRebuild = async () => {
    if (!window.confirm('This will rebuild the entire vector database. The process may take several minutes. Continue?')) {
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      await adminService.triggerRebuild();
      alert('Rebuild triggered successfully! The vector database is being updated in the background.');
      // Refresh health info after rebuild starts
      const health = await adminService.getHealth();
      setHealthInfo(health);
    } catch (err) {
      console.error('Error triggering rebuild:', err);
      setError('Failed to trigger rebuild. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    adminService.clearToken();
    navigate('/settings');
  };

  // Render Course Tree
  const renderCourseTree = (node, level = 0) => {
    const isSelected = selectedCourses.includes(node.path);
    
    // Check if all children are selected (for partial selection display)
    const getAllChildPaths = (n) => {
      let paths = [];
      if (n.children) {
        n.children.forEach(child => {
          paths.push(child.path);
          paths = paths.concat(getAllChildPaths(child));
        });
      }
      return paths;
    };
    
    const childPaths = getAllChildPaths(node);
    const allChildrenSelected = childPaths.length > 0 && childPaths.every(p => selectedCourses.includes(p));
    const someChildrenSelected = childPaths.some(p => selectedCourses.includes(p));
    
    return (
      <div key={node.path} style={{ marginLeft: `${level * 20}px` }} className="course-tree-item">
        <div className="course-item">
          <input
            type="checkbox"
            checked={isSelected || allChildrenSelected}
            ref={el => {
              if (el) {
                el.indeterminate = !isSelected && !allChildrenSelected && someChildrenSelected;
              }
            }}
            onChange={() => toggleCourseSelection(node.path, node)}
          />
          <span className={node.type === 'directory' ? 'directory-icon' : 'file-icon'}>
            {node.type === 'directory' ? '📁' : '📄'}
          </span>
          <span className="course-name">{node.name}</span>
          {node.type === 'file' && (
            <span className="course-size">({(node.size / 1024).toFixed(2)} KB)</span>
          )}
        </div>
        {node.children && node.children.map(child => renderCourseTree(child, level + 1))}
      </div>
    );
  };

  return (
    <div className="admin-page">
      <div className="admin-header">
        <div className="admin-header-content">
          <h1>Admin Dashboard</h1>
          <button className="btn-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </div>

      <div className="admin-container">
        {/* Tabs */}
        <div className="admin-tabs">
          <button
            className={`tab-btn ${activeTab === 'users' ? 'active' : ''}`}
            onClick={() => setActiveTab('users')}
          >
            👥 User Management
          </button>
          <button
            className={`tab-btn ${activeTab === 'courses' ? 'active' : ''}`}
            onClick={() => setActiveTab('courses')}
          >
            📚 Course Management
          </button>
          <button
            className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            ⚙️ System Settings
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="admin-error">
            <span>⚠️ {error}</span>
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {/* Tab Content */}
        <div className="admin-content">
          {loading && <div className="admin-loading">Loading...</div>}

          {/* User Management Tab */}
          {activeTab === 'users' && !loading && (
            <div className="users-section">
              <div className="section-header">
                <h2>Registered Users</h2>
                <button
                  className="btn-delete"
                  onClick={handleDeleteUsers}
                  disabled={selectedUsers.length === 0}
                >
                  Delete Selected ({selectedUsers.length})
                </button>
              </div>

              <div className="users-table">
                
                <table>
                  <thead>
                    <tr>
                      <th>
                        <input
                          type="checkbox"
                          checked={selectedUsers.length === users.length && users.length > 0}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedUsers(users.map(u => u.email));
                            } else {
                              setSelectedUsers([]);
                            }
                          }}
                        />
                      </th>
                      <th>Email</th>
                      <th>Name</th>
                      {/* <th>Chats</th> */}
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map(user => (
                      <tr key={user.email}>
                        <td>
                          <input
                            type="checkbox"
                            checked={selectedUsers.includes(user.email)}
                            onChange={() => toggleUserSelection(user.email)}
                          />
                        </td>
   
                        <td>{user.email}</td>
                        <td>{user.name}</td>
                        {/* <td>{user.chat_count}</td> */}
                        <td>{user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {users.length === 0 && (
                  <div className="empty-state">No users found</div>
                )}
              </div>
            </div>
          )}

          {/* Course Management Tab */}
          {activeTab === 'courses' && !loading && (
            <div className="courses-section">
              <div className="courses-two-column">
                {/* Left Column - Upload Section */}
                <div className="courses-left-column">
                  <div className="section-header-small">
                    <h3>Upload New Course</h3>
                  </div>
                  <div className="upload-section">
                    <div className="upload-form">
                      <div className="form-group">
                        <label>Select File (ZIP recommended):</label>
                        <input
                          type="file"
                          accept=".zip,.pdf,.pptx,.txt,.md,.py,.ipynb"
                          onChange={handleFileSelect}
                          disabled={uploading}
                        />
                        {uploadFile && <span className="file-name">{uploadFile.name}</span>}
                      </div>
                      <div className="form-group">
                        <label>Target Path:</label>
                        <div className="path-input-wrapper">
                          <input
                            type="text"
                            value={uploadPath}
                            onChange={handlePathInputChange}
                            onFocus={() => {
                              const suggestions = getFilteredSuggestions(uploadPath);
                              setPathSuggestions(suggestions);
                              setShowSuggestions(suggestions.length > 0);
                            }}
                            onBlur={() => {
                              // Delay hiding to allow click on suggestion
                              setTimeout(() => setShowSuggestions(false), 200);
                            }}
                            placeholder="CourseName/Folder"
                            disabled={uploading}
                            autoComplete="off"
                          />
                          {showSuggestions && pathSuggestions.length > 0 && (
                            <div className="path-suggestions">
                              {pathSuggestions.slice(0, 8).map((suggestion, index) => (
                                <div
                                  key={index}
                                  className="path-suggestion-item"
                                  onClick={() => handleSuggestionClick(suggestion)}
                                >
                                  📁 {suggestion}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        <small className="hint-text">e.g., CSC15/Week1 (type to see suggestions)</small>
                      </div>
                      <button
                        className="btn-upload"
                        onClick={handleUploadCourse}
                        disabled={!uploadFile || !uploadPath || uploading}
                      >
                        {uploading ? 'Uploading...' : 'Upload Course'}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Right Column - Course Tree */}
                <div className="courses-right-column">
                  <div className="section-header-small">
                    <h3>Existing Courses</h3>
                    <button
                      className="btn-delete-small"
                      onClick={handleDeleteCourses}
                      disabled={selectedCourses.length === 0}
                    >
                      Delete ({selectedCourses.length})
                    </button>
                  </div>
                  <div className="course-tree">
                    {courses.length === 0 ? (
                      <div className="empty-state">No courses found</div>
                    ) : (
                      <div className="course-list">
                        {courses.map(course => renderCourseTree(course))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* System Settings Tab */}
          {activeTab === 'settings' && !loading && (
            <div className="admin-settings-section">
              <h2>System Information</h2>
              
              {healthInfo && (
                <div className="health-info">
                  <div className="info-card">
                    <h3>Status</h3>
                    <p className={`status ${healthInfo.status}`}>{healthInfo.status}</p>
                  </div>
                  <div className="info-card">
                    <h3>Users Count</h3>
                    <p className="count">{users?.length}</p>
                  </div>
                  <div className="info-card">
                    <h3>Course File Count</h3>
                    <p className="count">{healthInfo.components.data.file_count}</p>
                  </div>
                  <div className="info-card">
                    <h3>Last Updated</h3>
                    <p>{new Date(healthInfo.timestamp).toLocaleString()}</p>
                  </div>
                </div>
              )}

              <div className="settings-actions">
                <div className="action-card">
                  <h3>Health Check Endpoint</h3>
                  <p className="endpoint-url">
                    <code>{adminService.baseURL}/health</code>
                  </p>
                </div>

                <div className="action-card">
                  <h3>Rebuild Vector Database</h3>
                  <p>Rebuild the vector database to include new course materials. This process runs in the background and may take several minutes.</p>
                  <button
                    className="btn-rebuild"
                    onClick={handleRebuild}
                    disabled={loading}
                  >
                    {loading ? 'Processing...' : 'Trigger Rebuild'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
