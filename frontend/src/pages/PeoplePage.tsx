import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { peopleApi } from '@/services/api';
import { Person } from '@/types';
import {
  UserGroupIcon,
  PencilIcon,
  TrashIcon,
  UserPlusIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

export default function PeoplePage() {
  const queryClient = useQueryClient();
  const [editingPerson, setEditingPerson] = useState<Person | null>(null);
  const [newName, setNewName] = useState('');
  
  // Fetch people
  const { data: people, isLoading } = useQuery<Person[]>({
    queryKey: ['people'],
    queryFn: async () => {
      const response = await peopleApi.list();
      return response.data;
    },
  });
  
  // Update person mutation
  const updatePerson = useMutation({
    mutationFn: async ({ id, name }: { id: string; name: string }) => {
      await peopleApi.update(id, name);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['people'] });
      setEditingPerson(null);
      setNewName('');
      toast.success('Person updated');
    },
  });
  
  // Delete person mutation
  const deletePerson = useMutation({
    mutationFn: async (id: string) => {
      await peopleApi.delete(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['people'] });
      toast.success('Person deleted');
    },
  });
  
  const handleEdit = (person: Person) => {
    setEditingPerson(person);
    setNewName(person.name || '');
  };
  
  const handleSave = () => {
    if (editingPerson && newName.trim()) {
      updatePerson.mutate({ id: editingPerson.id, name: newName.trim() });
    }
  };
  
  const namedPeople = people?.filter(p => p.is_named) || [];
  const unnamedPeople = people?.filter(p => !p.is_named) || [];
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">People</h1>
          <p className="text-dark-500 dark:text-dark-400">
            {people?.length || 0} people found in your photos
          </p>
        </div>
      </div>
      
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : people && people.length > 0 ? (
        <>
          {/* Named people */}
          {namedPeople.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-4">Named</h2>
              <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-4">
                {namedPeople.map((person) => (
                  <PersonCard
                    key={person.id}
                    person={person}
                    onEdit={() => handleEdit(person)}
                    onDelete={() => {
                      if (confirm('Delete this person?')) {
                        deletePerson.mutate(person.id);
                      }
                    }}
                  />
                ))}
              </div>
            </div>
          )}
          
          {/* Unnamed people */}
          {unnamedPeople.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-4">
                Unnamed ({unnamedPeople.length})
              </h2>
              <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-4">
                {unnamedPeople.map((person) => (
                  <PersonCard
                    key={person.id}
                    person={person}
                    onEdit={() => handleEdit(person)}
                    onDelete={() => {
                      if (confirm('Delete this person?')) {
                        deletePerson.mutate(person.id);
                      }
                    }}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-20">
          <UserGroupIcon className="w-16 h-16 mx-auto text-dark-300 mb-4" />
          <h3 className="text-lg font-medium mb-2">No people found</h3>
          <p className="text-dark-500">
            Face recognition will automatically detect people in your photos
          </p>
        </div>
      )}
      
      {/* Edit modal */}
      {editingPerson && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="card p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Name this person</h2>
            <div className="flex items-center gap-4 mb-4">
              <div className="w-20 h-20 rounded-full bg-dark-100 dark:bg-dark-700 overflow-hidden">
                {editingPerson.cover_face_thumbnail ? (
                  <img
                    src={editingPerson.cover_face_thumbnail}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <UserGroupIcon className="w-8 h-8 text-dark-300" />
                  </div>
                )}
              </div>
              <div>
                <p className="text-sm text-dark-500">{editingPerson.face_count} photos</p>
              </div>
            </div>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Enter name"
              className="input mb-4"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setEditingPerson(null)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button onClick={handleSave} className="btn-primary">
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PersonCard({
  person,
  onEdit,
  onDelete,
}: {
  person: Person;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="group relative">
      <Link to={`/people/${person.id}`} className="block">
        <div className="aspect-square rounded-full bg-dark-100 dark:bg-dark-700 overflow-hidden mb-2 group-hover:ring-2 ring-primary-500 transition-all">
          {person.cover_face_thumbnail ? (
            <img
              src={person.cover_face_thumbnail}
              alt={person.name || 'Unknown'}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <UserGroupIcon className="w-12 h-12 text-dark-300" />
            </div>
          )}
        </div>
        <p className="text-center font-medium truncate">
          {person.name || 'Add name'}
        </p>
        <p className="text-center text-sm text-dark-500">
          {person.face_count} photos
        </p>
      </Link>
      
      {/* Action buttons */}
      <div className="absolute top-0 right-0 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
        <button
          onClick={(e) => {
            e.preventDefault();
            onEdit();
          }}
          className="p-1.5 bg-white dark:bg-dark-800 rounded-full shadow hover:bg-dark-50"
        >
          <PencilIcon className="w-4 h-4" />
        </button>
        <button
          onClick={(e) => {
            e.preventDefault();
            onDelete();
          }}
          className="p-1.5 bg-white dark:bg-dark-800 rounded-full shadow hover:bg-red-50 text-red-600"
        >
          <TrashIcon className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
