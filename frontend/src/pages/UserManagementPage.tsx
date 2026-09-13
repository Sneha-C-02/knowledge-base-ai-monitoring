import { useEffect, useState } from "react";
import { api, type ManagedUser } from "../api/client";

const groups = [
    { id: 1, name: "Admin" },
    { id: 2, name: "Support Team" },
    { id: 3, name: "Normal User" },
];

const UserManagementPage = () => {
    const [users, setUsers] = useState<ManagedUser[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const loadUsers = async () => {
        try {
            const data = await api.getManagedUsers();
            if (!Array.isArray(data)) {
                throw new Error("Unable to load users.");
            }

            setUsers(data);
            setError("");
        } catch (err: any) {
            setUsers([]);
            setError(err?.message || "Unable to load users.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadUsers();
    }, []);

    const changeGroup = async (userId: number, groupId: number) => {
        await api.changeManagedUserGroup(userId, groupId);

        await loadUsers();
    };

    if (loading) {
        return <div>Loading users...</div>;
    }

    if (error) {
        return <div>{error}</div>;
    }

    return (
        <div>
            <h1>User Management</h1>

            {users.map((user) => (
                <div key={user.id}>
                    <span>{user.username}</span>

                    <select
                        value={user.group_id ?? ""}
                        onChange={(e) =>
                            changeGroup(user.id, Number(e.target.value))
                        }
                    >
                        {groups.map((group) => (
                            <option key={group.id} value={group.id}>
                                {group.name}
                            </option>
                        ))}
                    </select>
                </div>
            ))}
        </div>
    );
};

export default UserManagementPage;
