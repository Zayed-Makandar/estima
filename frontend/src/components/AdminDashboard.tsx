import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";

interface User {
    id: number;
    username: string;
    email: string;
    role: string;
    is_active: boolean;
}

const API_BASE = "http://localhost:8000";

export function AdminDashboard({ onClose }: { onClose: () => void }) {
    const { token, user: currentUser } = useAuth();
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [editingUser, setEditingUser] = useState<User | null>(null);

    // Form state
    const [formData, setFormData] = useState({
        username: "",
        email: "",
        password: "",
        role: "normal",
    });

    const fetchUsers = async () => {
        try {
            const resp = await fetch(`${API_BASE}/api/users`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (resp.ok) {
                const data = await resp.json();
                setUsers(data);
            } else {
                setError("Failed to fetch users");
            }
        } catch (e) {
            setError("Network error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, [token]);

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        try {
            const resp = await fetch(`${API_BASE}/api/users`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(formData),
            });

            if (resp.ok) {
                setShowCreateForm(false);
                setFormData({ username: "", email: "", password: "", role: "normal" });
                fetchUsers();
            } else {
                const data = await resp.json();
                setError(data.detail || "Failed to create user");
            }
        } catch (e) {
            setError("Network error");
        }
    };

    const handleUpdate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingUser) return;
        setError(null);

        const updateData: any = {};
        if (formData.username) updateData.username = formData.username;
        if (formData.email) updateData.email = formData.email;
        if (formData.password) updateData.password = formData.password;
        if (formData.role) updateData.role = formData.role;

        try {
            const resp = await fetch(`${API_BASE}/api/users/${editingUser.id}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(updateData),
            });

            if (resp.ok) {
                setEditingUser(null);
                setFormData({ username: "", email: "", password: "", role: "normal" });
                fetchUsers();
            } else {
                const data = await resp.json();
                setError(data.detail || "Failed to update user");
            }
        } catch (e) {
            setError("Network error");
        }
    };

    const handleDelete = async (userId: number) => {
        if (!confirm("Are you sure you want to delete this user?")) return;

        try {
            const resp = await fetch(`${API_BASE}/api/users/${userId}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` },
            });

            if (resp.ok) {
                fetchUsers();
            } else {
                const data = await resp.json();
                setError(data.detail || "Failed to delete user");
            }
        } catch (e) {
            setError("Network error");
        }
    };

    const handleToggleActive = async (user: User) => {
        try {
            const resp = await fetch(`${API_BASE}/api/users/${user.id}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ is_active: !user.is_active }),
            });

            if (resp.ok) {
                fetchUsers();
            }
        } catch (e) {
            setError("Network error");
        }
    };

    const startEdit = (user: User) => {
        setEditingUser(user);
        setFormData({
            username: user.username,
            email: user.email,
            password: "",
            role: user.role,
        });
        setShowCreateForm(false);
    };

    return (
        <div className="admin-backdrop" onClick={onClose}>
            <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
                <div className="admin-header">
                    <h2>User Management</h2>
                    <button className="admin-close-btn" onClick={onClose}>×</button>
                </div>

                {error && <div className="admin-error">{error}</div>}

                <div className="admin-actions">
                    <button
                        className="btn-primary"
                        onClick={() => {
                            setShowCreateForm(true);
                            setEditingUser(null);
                            setFormData({ username: "", email: "", password: "", role: "normal" });
                        }}
                    >
                        + Add User
                    </button>
                </div>

                {(showCreateForm || editingUser) && (
                    <form onSubmit={editingUser ? handleUpdate : handleCreate} className="admin-form">
                        <h3>{editingUser ? "Edit User" : "Create New User"}</h3>
                        <div className="form-row">
                            <div className="form-group">
                                <label>Username</label>
                                <input
                                    type="text"
                                    value={formData.username}
                                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                    required={!editingUser}
                                />
                            </div>
                            <div className="form-group">
                                <label>Email</label>
                                <input
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                    required={!editingUser}
                                />
                            </div>
                        </div>
                        <div className="form-row">
                            <div className="form-group">
                                <label>Password {editingUser && "(leave empty to keep)"}</label>
                                <input
                                    type="password"
                                    value={formData.password}
                                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                    required={!editingUser}
                                />
                            </div>
                            <div className="form-group">
                                <label>Role</label>
                                <select
                                    value={formData.role}
                                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                                >
                                    <option value="normal">Normal User</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                        </div>
                        <div className="form-actions">
                            <button type="submit" className="btn-primary">
                                {editingUser ? "Update" : "Create"}
                            </button>
                            <button
                                type="button"
                                className="btn-secondary"
                                onClick={() => {
                                    setShowCreateForm(false);
                                    setEditingUser(null);
                                }}
                            >
                                Cancel
                            </button>
                        </div>
                    </form>
                )}

                <div className="admin-users-table">
                    {loading ? (
                        <p>Loading users...</p>
                    ) : (
                        <table>
                            <thead>
                                <tr>
                                    <th>Username</th>
                                    <th>Email</th>
                                    <th>Role</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map((user) => (
                                    <tr key={user.id}>
                                        <td>{user.username}</td>
                                        <td>{user.email}</td>
                                        <td>
                                            <span className={`role-badge role-${user.role}`}>
                                                {user.role}
                                            </span>
                                        </td>
                                        <td>
                                            <span
                                                className={`status-badge ${user.is_active ? 'status-active' : 'status-inactive'}`}
                                                onClick={() => handleToggleActive(user)}
                                                style={{ cursor: 'pointer' }}
                                            >
                                                {user.is_active ? "Active" : "Inactive"}
                                            </span>
                                        </td>
                                        <td>
                                            <button
                                                className="btn-edit"
                                                onClick={() => startEdit(user)}
                                            >
                                                Edit
                                            </button>
                                            {user.id !== currentUser?.id && (
                                                <button
                                                    className="btn-delete"
                                                    onClick={() => handleDelete(user.id)}
                                                >
                                                    Delete
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </div>
    );
}
