import { useEffect, useState } from "react";
import { api, type ManagedUser } from "../api/client";

const groups = [
    { id: 1, name: "Admin" },
    { id: 2, name: "Support Team" },
    { id: 3, name: "Normal User" },
];

const getGroupName = (groupId: number | null) => {
    return groups.find((group) => group.id === groupId)?.name ?? "Unknown";
};

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
        try {
            await api.changeManagedUserGroup(userId, groupId);
            await loadUsers();
        } catch (err: any) {
            setError(err?.message || "Failed to update user group.");
        }
    };

    const resetPassword = (username: string) => {
        alert(`Reset password for ${username}`);
    };

    if (loading) {
        return (
            <div className="p-6">
                <h1 className="text-2xl font-bold text-slate-900 mb-6">
                    User Management
                </h1>

                <div className="bg-white rounded-xl border border-slate-200 p-6">
                    Loading users...
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <h1 className="text-2xl font-bold text-slate-900 mb-6">
                    User Management
                </h1>

                <div className="bg-white rounded-xl border border-red-200 p-6 text-red-600">
                    {error}
                </div>
            </div>
        );
    }

    return (
        <div className="p-6">
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-slate-900">
                    User Management
                </h1>

                <p className="text-sm text-slate-500 mt-1">
                    Manage users, groups, and account passwords.
                </p>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-slate-50 border-b border-slate-200">
                            <tr>
                                <th className="px-6 py-4 text-sm font-semibold text-slate-700">
                                    Username
                                </th>

                                <th className="px-6 py-4 text-sm font-semibold text-slate-700">
                                    Group
                                </th>

                                <th className="px-6 py-4 text-sm font-semibold text-slate-700">
                                    Password
                                </th>

                                <th className="px-6 py-4 text-sm font-semibold text-slate-700">
                                    Actions
                                </th>
                            </tr>
                        </thead>

                        <tbody className="divide-y divide-slate-200">
                            {users.map((user) => (
                                <tr
                                    key={user.id}
                                    className="hover:bg-slate-50 transition-colors"
                                >
                                    <td className="px-6 py-4">
                                        <span className="font-medium text-slate-900">
                                            {user.username}
                                        </span>
                                    </td>

                                    <td className="px-6 py-4">
                                        <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
                                            {getGroupName(user.group_id)}
                                        </span>
                                    </td>

                                    <td className="px-6 py-4">
                                        <span className="text-slate-500 tracking-widest">
                                            ••••••••
                                        </span>
                                    </td>

                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <select
                                                value={user.group_id ?? ""}
                                                onChange={(e) =>
                                                    changeGroup(user.id, Number(e.target.value))
                                                }
                                                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
                                            >
                                                {groups.map((group) => (
                                                    <option key={group.id} value={group.id}>
                                                        {group.name}
                                                    </option>
                                                ))}
                                            </select>

                                            <button
                                                type="button"
                                                onClick={() => resetPassword(user.username)}
                                                className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
                                            >
                                                Reset Password
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {users.length === 0 && (
                <div className="mt-6 text-center text-slate-500">
                    No users found.
                </div>
            )}
        </div>
    );
};

export default UserManagementPage;