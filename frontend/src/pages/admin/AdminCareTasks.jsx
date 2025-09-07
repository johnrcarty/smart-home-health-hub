import React, { useState, useEffect } from 'react';
import config from '../../config';

const AdminCareTasks = () => {
  const [careTasks, setCareTasks] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('active'); // 'active', 'inactive', 'categories'
  const [showAddForm, setShowAddForm] = useState(false);
  const [showAddCategoryForm, setShowAddCategoryForm] = useState(false);
  const [error, setError] = useState(null);
  
  const [newCareTask, setNewCareTask] = useState({
    name: '',
    description: '',
    category_id: '',
    estimated_duration_minutes: 30,
    instructions: '',
    notes: ''
  });

  const [newCategory, setNewCategory] = useState({
    name: '',
    description: '',
    color: '#007acc'
  });

  useEffect(() => {
    fetchData();
    fetchCategories();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const endpoint = activeTab === 'active' ? '/api/care-tasks/active' : '/api/care-tasks/inactive';
      const response = await fetch(`${config.apiUrl}${endpoint}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setCareTasks(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error fetching care tasks:', error);
      setError(`Failed to fetch care tasks: ${error.message}`);
      setCareTasks([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${config.apiUrl}/api/care-task-categories`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setCategories(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error fetching categories:', error);
      setCategories([]);
    }
  };

  const handleAddCareTask = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${config.apiUrl}/api/add/care-task`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newCareTask),
      });

      if (response.ok) {
        setShowAddForm(false);
        setNewCareTask({
          name: '',
          description: '',
          category_id: '',
          estimated_duration_minutes: 30,
          instructions: '',
          notes: ''
        });
        fetchData();
      } else {
        console.error('Failed to add care task');
      }
    } catch (error) {
      console.error('Error adding care task:', error);
    }
  };

  const handleAddCategory = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${config.apiUrl}/api/add/care-task-category`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newCategory),
      });

      if (response.ok) {
        setShowAddCategoryForm(false);
        setNewCategory({
          name: '',
          description: '',
          color: '#007acc'
        });
        fetchCategories();
      } else {
        console.error('Failed to add category');
      }
    } catch (error) {
      console.error('Error adding category:', error);
    }
  };

  const handleToggleActive = async (taskId) => {
    try {
      const response = await fetch(`${config.apiUrl}/api/care-tasks/${taskId}/toggle-active`, {
        method: 'POST',
      });

      if (response.ok) {
        fetchData();
      } else {
        console.error('Failed to toggle care task status');
      }
    } catch (error) {
      console.error('Error toggling care task status:', error);
    }
  };

  const handleDeleteCareTask = async (taskId) => {
    if (window.confirm('Are you sure you want to delete this care task?')) {
      try {
        const response = await fetch(`${config.apiUrl}/api/care-tasks/${taskId}`, {
          method: 'DELETE',
        });

        if (response.ok) {
          fetchData();
        } else {
          console.error('Failed to delete care task');
        }
      } catch (error) {
        console.error('Error deleting care task:', error);
      }
    }
  };

  const handleDeleteCategory = async (categoryId) => {
    if (window.confirm('Are you sure you want to delete this category? This will affect all care tasks using this category.')) {
      try {
        const response = await fetch(`${config.apiUrl}/api/care-task-categories/${categoryId}`, {
          method: 'DELETE',
        });

        if (response.ok) {
          fetchCategories();
        } else {
          console.error('Failed to delete category');
        }
      } catch (error) {
        console.error('Error deleting category:', error);
      }
    }
  };

  const getCategoryName = (categoryId) => {
    const category = categories.find(cat => cat.id === categoryId);
    return category ? category.name : 'Unknown';
  };

  const getCategoryColor = (categoryId) => {
    const category = categories.find(cat => cat.id === categoryId);
    return category ? category.color : '#666';
  };

  if (loading) {
    return <div className="admin-page">
      <div className="loading">Loading care tasks...</div>
    </div>;
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1 className="admin-page-title">Care Task Management</h1>
        <p className="admin-page-description">
          Manage care tasks, categories, and scheduling
        </p>
      </div>

      <div className="admin-section">
        <div className="admin-section-header">
          <h2 className="admin-section-title">Care Tasks</h2>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <div className="tab-buttons" style={{ display: 'flex', gap: '0.5rem' }}>
              <button 
                className={`btn ${activeTab === 'active' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('active')}
              >
                Active ({careTasks.length})
              </button>
              <button 
                className={`btn ${activeTab === 'inactive' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('inactive')}
              >
                Inactive
              </button>
              <button 
                className={`btn ${activeTab === 'categories' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('categories')}
              >
                Categories ({categories.length})
              </button>
            </div>
            {activeTab === 'categories' ? (
              <button 
                className="btn btn-success"
                onClick={() => setShowAddCategoryForm(true)}
              >
                + Add Category
              </button>
            ) : (
              <button 
                className="btn btn-success"
                onClick={() => setShowAddForm(true)}
              >
                + Add Care Task
              </button>
            )}
          </div>
        </div>

        <div className="admin-section-content">
          {showAddForm && (
            <div className="admin-card" style={{ marginBottom: '2rem', background: '#f8f9fa' }}>
              <h3 className="admin-card-title">Add New Care Task</h3>
              <form onSubmit={handleAddCareTask}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Name *</label>
                    <input
                      type="text"
                      required
                      value={newCareTask.name}
                      onChange={(e) => setNewCareTask({ ...newCareTask, name: e.target.value })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Category</label>
                    <select
                      value={newCareTask.category_id}
                      onChange={(e) => setNewCareTask({ ...newCareTask, category_id: e.target.value })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    >
                      <option value="">Select Category</option>
                      {categories.map((category) => (
                        <option key={category.id} value={category.id}>
                          {category.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Duration (minutes)</label>
                    <input
                      type="number"
                      min="1"
                      value={newCareTask.estimated_duration_minutes}
                      onChange={(e) => setNewCareTask({ ...newCareTask, estimated_duration_minutes: parseInt(e.target.value) })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    />
                  </div>
                </div>
                
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Description</label>
                  <textarea
                    value={newCareTask.description}
                    onChange={(e) => setNewCareTask({ ...newCareTask, description: e.target.value })}
                    style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px', minHeight: '80px' }}
                  />
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Instructions</label>
                  <textarea
                    value={newCareTask.instructions}
                    onChange={(e) => setNewCareTask({ ...newCareTask, instructions: e.target.value })}
                    style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px', minHeight: '100px' }}
                  />
                </div>

                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Notes</label>
                  <textarea
                    value={newCareTask.notes}
                    onChange={(e) => setNewCareTask({ ...newCareTask, notes: e.target.value })}
                    style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px', minHeight: '60px' }}
                  />
                </div>

                <div className="admin-actions">
                  <button type="submit" className="btn btn-success">
                    Add Care Task
                  </button>
                  <button 
                    type="button" 
                    className="btn btn-secondary"
                    onClick={() => setShowAddForm(false)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {showAddCategoryForm && (
            <div className="admin-card" style={{ marginBottom: '2rem', background: '#f8f9fa' }}>
              <h3 className="admin-card-title">Add New Category</h3>
              <form onSubmit={handleAddCategory}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Name *</label>
                    <input
                      type="text"
                      required
                      value={newCategory.name}
                      onChange={(e) => setNewCategory({ ...newCategory, name: e.target.value })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Color</label>
                    <input
                      type="color"
                      value={newCategory.color}
                      onChange={(e) => setNewCategory({ ...newCategory, color: e.target.value })}
                      style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
                    />
                  </div>
                </div>
                
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>Description</label>
                  <textarea
                    value={newCategory.description}
                    onChange={(e) => setNewCategory({ ...newCategory, description: e.target.value })}
                    style={{ width: '100%', padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px', minHeight: '80px' }}
                  />
                </div>

                <div className="admin-actions">
                  <button type="submit" className="btn btn-success">
                    Add Category
                  </button>
                  <button 
                    type="button" 
                    className="btn btn-secondary"
                    onClick={() => setShowAddCategoryForm(false)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {activeTab === 'categories' ? (
            <div className="admin-grid">
              {categories.map((category) => (
                <div key={category.id} className="admin-card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                    <div 
                      style={{ 
                        width: '20px', 
                        height: '20px', 
                        backgroundColor: category.color, 
                        borderRadius: '4px' 
                      }}
                    ></div>
                    <h3 className="admin-card-title" style={{ margin: 0 }}>
                      {category.name}
                    </h3>
                  </div>
                  <p style={{ color: '#666', marginBottom: '1rem' }}>
                    {category.description || 'No description available'}
                  </p>
                  <div className="admin-actions">
                    <button 
                      className="btn btn-danger"
                      onClick={() => handleDeleteCategory(category.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Duration</th>
                  <th>Description</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {careTasks.map((task) => (
                  <tr key={task.id}>
                    <td style={{ fontWeight: '600' }}>{task.name}</td>
                    <td>
                      {task.category_id && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div 
                            style={{ 
                              width: '12px', 
                              height: '12px', 
                              backgroundColor: getCategoryColor(task.category_id), 
                              borderRadius: '2px' 
                            }}
                          ></div>
                          {getCategoryName(task.category_id)}
                        </div>
                      )}
                    </td>
                    <td>{task.estimated_duration_minutes} min</td>
                    <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {task.description}
                    </td>
                    <td>
                      <span className={`status-badge ${task.active ? 'status-active' : 'status-inactive'}`}>
                        {task.active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <button 
                          className={`btn ${task.active ? 'btn-warning' : 'btn-success'}`}
                          style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                          onClick={() => handleToggleActive(task.id)}
                        >
                          {task.active ? 'Deactivate' : 'Activate'}
                        </button>
                        <button 
                          className="btn btn-danger"
                          style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}
                          onClick={() => handleDeleteCareTask(task.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {careTasks.length === 0 && activeTab !== 'categories' && (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
              No {activeTab} care tasks found.
            </div>
          )}

          {categories.length === 0 && activeTab === 'categories' && (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
              No categories found. Add a category to organize your care tasks.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminCareTasks;
